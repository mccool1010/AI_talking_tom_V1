extends Node3D
## Main controller for AI Talking Tom's Godot embodiment.
##
## Connects to the Python backend via TCP (JSON lines protocol)
## and drives Tom's animations based on received events.
## Uses the model's 62 BUILT-IN animations from the GLB file.
##
## Animation naming convention from the model:
##   Suffix 'A' = one-shot Action
##   Suffix 'L' = Looping pose
##   Suffix 'D' = Default emotion, 'H' = Happy, 'S' = Sad

# --- Node references ---
var tom_model: Node3D
var skeleton: Skeleton3D
var anim_player: AnimationPlayer
var camera: Camera3D

# --- TCP connection ---
var tcp: StreamPeerTCP
var buffer: String = ""
const HOST: String = "127.0.0.1"
const PORT: int = 9090
var connected: bool = false
var reconnect_timer: float = 0.0

# --- Animation state ---
var is_speaking: bool = false
var current_emotion: String = "neutral"
var blink_timer: float = 0.0
var idle_fidget_timer: float = 0.0

# --- Mouth movement while speaking ---
# A SkeletonModifier3D opens the jaw after the AnimationPlayer has run.
# The backend sends the loudness envelope of each spoken line so the mouth
# opens on syllables and closes in pauses.
const JawModifier := preload("res://scripts/jaw_modifier.gd")
var jaw_modifier: JawModifier
var speech_envelope: Array = []
var envelope_fps: float = 20.0
var speech_time: float = 0.0
var mouth_openness: float = 0.0
var loudness_average: float = 0.0
## Audio reaches the speakers a little after the speak event arrives.
const AUDIO_LATENCY: float = 0.08


func _ready() -> void:
	print("[Tom] Starting up...")

	tom_model = $TomModel

	if tom_model:
		print("[Tom] Model found in scene tree")
		_find_skeleton()
		_find_animation_player()

		# Start the breathing idle loop
		if anim_player:
			_play_idle()
			if jaw_modifier:
				jaw_modifier.set_talk_animation(_talk_animation_for("neutral"))

		# --- Camera: portrait framing ---
		var aabb := _get_combined_aabb(tom_model)
		var center := aabb.get_center()
		var model_height: float = aabb.size.y
		print("[Tom] Model AABB center=", center, " height=", model_height)

		# Try camera from +Z first (standard GLB facing -Z toward camera)
		var face_y: float = center.y + model_height * 0.05
		var cam_dist: float = max(model_height * 2.0, 4.0)
		camera = Camera3D.new()
		camera.position = Vector3(0, face_y, cam_dist)
		camera.fov = 30.0
		camera.far = model_height * 20.0
		camera.current = true
		add_child(camera)
		camera.look_at(Vector3(0, center.y + model_height * 0.05, 0))
		print("[Tom] Camera at ", camera.position, " looking at center_y=", center.y)
	else:
		push_error("[Tom] TomModel node not found!")
		camera = Camera3D.new()
		camera.position = Vector3(0, 1, 3)
		camera.current = true
		add_child(camera)

	# --- BUILD ROOM ---
	_build_room()

	# --- PRO LIGHTING ---
	var key_light := DirectionalLight3D.new()
	key_light.rotation_degrees = Vector3(-35, 25, 0)
	key_light.light_energy = 1.6
	key_light.light_color = Color(1.0, 0.95, 0.88)
	key_light.shadow_enabled = true
	add_child(key_light)

	var fill_light := DirectionalLight3D.new()
	fill_light.rotation_degrees = Vector3(-15, -45, 0)
	fill_light.light_energy = 0.5
	fill_light.light_color = Color(0.85, 0.9, 1.0)
	add_child(fill_light)

	var rim_light := DirectionalLight3D.new()
	rim_light.rotation_degrees = Vector3(-5, 170, 0)
	rim_light.light_energy = 0.7
	rim_light.light_color = Color(0.7, 0.8, 1.0)
	add_child(rim_light)

	var world_env := WorldEnvironment.new()
	var env := Environment.new()
	env.background_mode = Environment.BG_COLOR
	env.background_color = Color(0.08, 0.08, 0.12)
	env.ambient_light_color = Color(0.5, 0.48, 0.45)
	env.ambient_light_energy = 0.5
	env.ssao_enabled = true
	env.glow_enabled = true
	env.glow_intensity = 0.3
	env.glow_bloom = 0.1
	world_env.environment = env
	add_child(world_env)

	_setup_tcp()
	blink_timer = randf_range(2.0, 5.0)
	idle_fidget_timer = randf_range(6.0, 12.0)


# ---------------------------------------------------------------
# Room construction — cozy Talking Tom living room
# ---------------------------------------------------------------

func _build_room() -> void:
	var room := Node3D.new()
	room.name = "Room"
	add_child(room)

	# --- Floor (wooden) ---
	var floor_mesh := MeshInstance3D.new()
	var floor_plane := PlaneMesh.new()
	floor_plane.size = Vector2(8, 8)
	floor_mesh.mesh = floor_plane
	var floor_mat := StandardMaterial3D.new()
	floor_mat.albedo_color = Color(0.45, 0.32, 0.2)  # warm wood
	floor_mat.roughness = 0.85
	floor_mesh.material_override = floor_mat
	floor_mesh.position = Vector3(0, 0, 0)
	room.add_child(floor_mesh)

	# --- Back wall ---
	var back_wall := MeshInstance3D.new()
	var bw_mesh := BoxMesh.new()
	bw_mesh.size = Vector3(8, 5, 0.15)
	back_wall.mesh = bw_mesh
	var wall_mat := StandardMaterial3D.new()
	wall_mat.albedo_color = Color(0.72, 0.78, 0.85)  # soft blue-grey
	wall_mat.roughness = 0.9
	back_wall.material_override = wall_mat
	back_wall.position = Vector3(0, 2.5, -4)
	room.add_child(back_wall)

	# --- Left wall ---
	var left_wall := MeshInstance3D.new()
	var lw_mesh := BoxMesh.new()
	lw_mesh.size = Vector3(0.15, 5, 8)
	left_wall.mesh = lw_mesh
	left_wall.material_override = wall_mat
	left_wall.position = Vector3(-4, 2.5, 0)
	room.add_child(left_wall)

	# --- Right wall ---
	var right_wall := MeshInstance3D.new()
	var rw_mesh := BoxMesh.new()
	rw_mesh.size = Vector3(0.15, 5, 8)
	right_wall.mesh = rw_mesh
	right_wall.material_override = wall_mat
	right_wall.position = Vector3(4, 2.5, 0)
	room.add_child(right_wall)

	# --- Window frame on back wall ---
	var window_frame := MeshInstance3D.new()
	var wf_mesh := BoxMesh.new()
	wf_mesh.size = Vector3(1.8, 2.2, 0.08)
	window_frame.mesh = wf_mesh
	var frame_mat := StandardMaterial3D.new()
	frame_mat.albedo_color = Color(0.9, 0.9, 0.85)  # cream white frame
	frame_mat.roughness = 0.5
	window_frame.material_override = frame_mat
	window_frame.position = Vector3(0, 2.8, -3.9)
	room.add_child(window_frame)

	# --- Window "glass" (bright sky glow) ---
	var window_glass := MeshInstance3D.new()
	var wg_mesh := BoxMesh.new()
	wg_mesh.size = Vector3(1.5, 1.8, 0.02)
	window_glass.mesh = wg_mesh
	var glass_mat := StandardMaterial3D.new()
	glass_mat.albedo_color = Color(0.6, 0.75, 0.95)
	glass_mat.emission_enabled = true
	glass_mat.emission = Color(0.5, 0.65, 0.9)
	glass_mat.emission_energy_multiplier = 1.5
	window_glass.material_override = glass_mat
	window_glass.position = Vector3(0, 2.8, -3.88)
	room.add_child(window_glass)

	# --- Window light (OmniLight simulating sunlight from window) ---
	var window_light := OmniLight3D.new()
	window_light.position = Vector3(0, 2.8, -3.5)
	window_light.light_energy = 2.0
	window_light.light_color = Color(1.0, 0.95, 0.85)
	window_light.omni_range = 5.0
	window_light.omni_attenuation = 1.5
	room.add_child(window_light)

	# --- Round rug on floor ---
	var rug := MeshInstance3D.new()
	var rug_mesh := CylinderMesh.new()
	rug_mesh.top_radius = 1.2
	rug_mesh.bottom_radius = 1.2
	rug_mesh.height = 0.02
	rug.mesh = rug_mesh
	var rug_mat := StandardMaterial3D.new()
	rug_mat.albedo_color = Color(0.6, 0.2, 0.25)  # deep red rug
	rug_mat.roughness = 0.95
	rug.material_override = rug_mat
	rug.position = Vector3(0, 0.01, 0)
	room.add_child(rug)

	# --- Small shelf on left wall ---
	var shelf := MeshInstance3D.new()
	var shelf_mesh := BoxMesh.new()
	shelf_mesh.size = Vector3(0.15, 1.8, 0.6)
	shelf.mesh = shelf_mesh
	var shelf_mat := StandardMaterial3D.new()
	shelf_mat.albedo_color = Color(0.35, 0.25, 0.15)  # dark wood
	shelf_mat.roughness = 0.7
	shelf.material_override = shelf_mat
	shelf.position = Vector3(-3.5, 0.9, -2.5)
	room.add_child(shelf)

	# --- Small table on right ---
	var table := MeshInstance3D.new()
	var table_mesh := BoxMesh.new()
	table_mesh.size = Vector3(0.8, 0.6, 0.5)
	table.mesh = table_mesh
	table.material_override = shelf_mat  # same dark wood
	table.position = Vector3(2.8, 0.3, -2.0)
	room.add_child(table)

	# --- Ceiling ---
	var ceiling := MeshInstance3D.new()
	var ceil_mesh := PlaneMesh.new()
	ceil_mesh.size = Vector2(8, 8)
	ceiling.mesh = ceil_mesh
	var ceil_mat := StandardMaterial3D.new()
	ceil_mat.albedo_color = Color(0.88, 0.88, 0.85)  # off-white
	ceiling.material_override = ceil_mat
	ceiling.position = Vector3(0, 5, 0)
	ceiling.rotation_degrees.x = 180  # flip to face down
	room.add_child(ceiling)

	# --- Baseboard trim (bottom of walls) ---
	var baseboard := MeshInstance3D.new()
	var bb_mesh := BoxMesh.new()
	bb_mesh.size = Vector3(8, 0.12, 0.08)
	baseboard.mesh = bb_mesh
	var bb_mat := StandardMaterial3D.new()
	bb_mat.albedo_color = Color(0.9, 0.88, 0.82)
	baseboard.material_override = bb_mat
	baseboard.position = Vector3(0, 0.06, -3.93)
	room.add_child(baseboard)

	print("[Tom] Room built: floor, walls, window, furniture")


# ---------------------------------------------------------------
# Animation system — uses the model's 62 built-in animations
# ---------------------------------------------------------------

## Get the emotion suffix: D=default, H=happy, S=sad
func _emotion_suffix() -> String:
	match current_emotion:
		"happy", "excited", "amused":
			return "H"
		"sad", "tired", "bored":
			return "S"
		_:
			return "D"


## Play the correct idle animation (breathingL for looping idle)
func _play_idle() -> void:
	if not anim_player:
		return
	if anim_player.current_animation == "breathingL":
		return
	if anim_player.has_animation("breathingL"):
		anim_player.play("breathingL", 0.25)
	elif anim_player.has_animation("happyL"):
		anim_player.play("happyL", 0.25)


## Start speaking — keep breathingL running, jaw bone handles mouth
func _play_talk() -> void:
	if not anim_player:
		return
	# Stay on breathingL (looping, no facial pose resets)
	# Jaw bone overlay handles mouth opening
	if anim_player.current_animation != "breathingL":
		anim_player.play("breathingL", 0.25)
	print("[Tom] → speaking (jaw overlay on breathingL)")


## Play blink animation matching current emotion
func _play_blink() -> void:
	if not anim_player:
		return
	if anim_player.current_animation != "breathingL":
		return
	# Always use default blink — emotion variants cause face flicker
	if anim_player.has_animation("blinkAD"):
		anim_player.play("blinkAD", 0.05)


## Play a head nod matching current emotion
func _play_nod() -> void:
	if not anim_player:
		return
	var anim_name := "nodsAD"
	if anim_player.has_animation(anim_name):
		anim_player.play(anim_name, 0.2)


## Play head shake matching current emotion
func _play_head_shake() -> void:
	if not anim_player:
		return
	var anim_name := "shakesHeadAD"
	if anim_player.has_animation(anim_name):
		anim_player.play(anim_name, 0.2)


## Play a random idle fidget (reactions, yawns, etc.)
func _play_random_fidget() -> void:
	if not anim_player or is_speaking:
		return
	# Only fidget during idle breathing — never interrupt other anims
	if anim_player.current_animation != "breathingL":
		return
	var fidgets: Array[String] = [
		"reactionEyeRollA",
		"reactionSighsA",
		"shoulderShrugL",
		"reactionMmmmA",
		"nodsAD",
	]
	fidgets.shuffle()
	for f in fidgets:
		if anim_player.has_animation(f):
			anim_player.play(f, 0.3)
			print("[Tom] → fidget (", f, ")")
			return


## Play the listen pose
func _play_listen() -> void:
	if not anim_player:
		return
	if anim_player.has_animation("listenL"):
		anim_player.play("listenL", 0.3)
		print("[Tom] → listen")


# ---------------------------------------------------------------
# Skeleton / helpers
# ---------------------------------------------------------------

func _find_skeleton() -> void:
	skeleton = _find_node_of_type(tom_model, "Skeleton3D") as Skeleton3D
	if skeleton:
		print("[Tom] Skeleton: ", skeleton.get_bone_count(), " bones")
		jaw_modifier = JawModifier.new()
		jaw_modifier.name = "JawModifier"
		skeleton.add_child(jaw_modifier)
	else:
		print("[Tom] No skeleton found")


func _find_animation_player() -> void:
	anim_player = _find_node_of_type(tom_model, "AnimationPlayer") as AnimationPlayer
	if anim_player:
		var anims := anim_player.get_animation_list()
		print("[Tom] AnimationPlayer found with ", anims.size(), " animations")
		# Make breathing loop
		if anim_player.has_animation("breathingL"):
			var breathing := anim_player.get_animation("breathingL")
			breathing.loop_mode = Animation.LOOP_LINEAR
			print("[Tom] Set breathingL to loop")
		# Also loop listen
		if anim_player.has_animation("listenL"):
			var listen := anim_player.get_animation("listenL")
			listen.loop_mode = Animation.LOOP_LINEAR
		# Loop all talk animations for seamless speech
		for talk_name in ["talkAD", "talkAH", "talkAS"]:
			if anim_player.has_animation(talk_name):
				var talk := anim_player.get_animation(talk_name)
				talk.loop_mode = Animation.LOOP_LINEAR
				print("[Tom] Set ", talk_name, " to loop")

		# Connect animation_finished to auto-return to idle
		anim_player.animation_finished.connect(_on_animation_finished)
	else:
		print("[Tom] No AnimationPlayer found")


func _on_animation_finished(anim_name: StringName) -> void:
	var anim_str := String(anim_name)
	if anim_str in ["breathingL", "listenL"]:
		return  # looping, ignore
	# One-shot finished → return to breathing idle
	_play_idle()


func _find_node_of_type(node: Node, type_name: String) -> Node:
	if node.get_class() == type_name:
		return node
	for child in node.get_children():
		var found := _find_node_of_type(child, type_name)
		if found:
			return found
	return null


func _get_combined_aabb(node: Node) -> AABB:
	var aabbs: Array = []
	_collect_aabbs(node, aabbs)
	if aabbs.is_empty():
		return AABB(Vector3.ZERO, Vector3.ONE)
	var result: AABB = aabbs[0]
	for i in range(1, aabbs.size()):
		result = result.merge(aabbs[i])
	return result


func _collect_aabbs(node: Node, out: Array) -> void:
	if node is MeshInstance3D:
		var mi := node as MeshInstance3D
		var mesh_aabb := mi.get_aabb()
		var global_aabb := mi.global_transform * mesh_aabb
		out.append(global_aabb)
	for child in node.get_children():
		_collect_aabbs(child, out)


# ---------------------------------------------------------------
# TCP Connection
# ---------------------------------------------------------------

func _setup_tcp() -> void:
	tcp = StreamPeerTCP.new()
	_connect_tcp()


func _connect_tcp() -> void:
	var err := tcp.connect_to_host(HOST, PORT)
	if err == OK:
		print("[Tom] Connecting to Python backend at ", HOST, ":", PORT)
	else:
		print("[Tom] TCP connect failed, will retry...")


func _process_tcp() -> void:
	tcp.poll()
	var status := tcp.get_status()

	if status == StreamPeerTCP.STATUS_CONNECTED:
		if not connected:
			connected = true
			print("[Tom] Connected to Python backend!")

		while tcp.get_available_bytes() > 0:
			var data := tcp.get_utf8_string(tcp.get_available_bytes())
			buffer += data

		while "\n" in buffer:
			var newline_pos := buffer.find("\n")
			var line := buffer.substr(0, newline_pos).strip_edges()
			buffer = buffer.substr(newline_pos + 1)
			if line.length() > 0:
				_handle_event(line)

	elif status == StreamPeerTCP.STATUS_NONE or status == StreamPeerTCP.STATUS_ERROR:
		if connected:
			connected = false
			print("[Tom] Disconnected from Python backend")
		reconnect_timer -= get_process_delta_time()
		if reconnect_timer <= 0:
			reconnect_timer = 3.0
			_connect_tcp()


# ---------------------------------------------------------------
# Event handling
# ---------------------------------------------------------------

func _handle_event(json_str: String) -> void:
	var json := JSON.new()
	var err := json.parse(json_str)
	if err != OK:
		print("[Tom] Invalid JSON: ", json_str)
		return

	var data: Dictionary = json.data
	var event_type: String = data.get("type", "")

	match event_type:
		"speak":
			_on_speak(data.get("text", ""), data.get("emotion", "neutral"),
				data.get("envelope", []), float(data.get("fps", 20.0)))
		"speak_end":
			_on_speak_end()
		"emotion":
			_on_emotion(data.get("value", "neutral"))
		"idle":
			_on_idle_action(data.get("action", "blink"))
		"state":
			_on_state_change(data.get("phase", "idle"))
		_:
			print("[Tom] Unknown event: ", event_type)


func _on_speak(text: String, emotion: String, envelope: Array = [], fps: float = 20.0) -> void:
	is_speaking = true
	speech_time = 0.0
	speech_envelope = envelope
	envelope_fps = max(fps, 1.0)
	current_emotion = emotion
	if jaw_modifier:
		jaw_modifier.set_talk_animation(_talk_animation_for(emotion))
		jaw_modifier.restart()
	print("[Tom] Speaking: ", text.substr(0, 40), "...")
	_play_talk()


func _on_speak_end() -> void:
	is_speaking = false
	print("[Tom] Done speaking")
	_play_idle()


func _on_emotion(emotion: String) -> void:
	current_emotion = emotion


func _on_idle_action(action: String) -> void:
	if is_speaking:
		return
	match action:
		"blink":
			_play_blink()
		"nod":
			_play_nod()
		"head_shake":
			_play_head_shake()
		"yawn":
			if anim_player and anim_player.has_animation("yawnA"):
				anim_player.play("yawnA")
				anim_player.queue("breathingL")
		"stretch":
			_play_random_fidget()
		"look_left":
			if anim_player and anim_player.has_animation("hungryLookLeftLoopA"):
				anim_player.play("hungryLookLeftLoopA")
				anim_player.queue("breathingL")
		"look_right":
			if anim_player and anim_player.has_animation("hungryLookRightLoopA"):
				anim_player.play("hungryLookRightLoopA")
				anim_player.queue("breathingL")
		_:
			pass


func _on_state_change(phase: String) -> void:
	match phase:
		"listening":
			print("[Tom] State: Listening")
			_play_listen()
		"speaking":
			print("[Tom] State: Speaking")
		"idle":
			print("[Tom] State: Idle")
			_play_idle()


# ---------------------------------------------------------------
# Auto blink & idle fidgets
# ---------------------------------------------------------------

func _process(delta: float) -> void:
	_process_tcp()
	_animate_jaw(delta)

	# Auto-blink every 4-8 seconds (only during idle)
	blink_timer -= delta
	if blink_timer <= 0:
		_play_blink()
		blink_timer = randf_range(4.0, 8.0)

	# Random idle fidgets every 20-40 seconds (only when idle, not speaking)
	if not is_speaking:
		idle_fidget_timer -= delta
		if idle_fidget_timer <= 0:
			_play_random_fidget()
			idle_fidget_timer = randf_range(20.0, 40.0)


# ---------------------------------------------------------------
# Mouth movement for speech
# ---------------------------------------------------------------

func _talk_animation_for(emotion: String) -> Animation:
	if anim_player == null:
		return null
	var anim_name := "talkAD"
	match emotion:
		"happy", "surprise":
			anim_name = "talkAH"
		"sad", "fear":
			anim_name = "talkAS"
	if not anim_player.has_animation(anim_name):
		anim_name = "talkAD"
	return anim_player.get_animation(anim_name) if anim_player.has_animation(anim_name) else null


func _animate_jaw(delta: float) -> void:
	if jaw_modifier == null:
		return
	var target := 0.0
	if is_speaking:
		speech_time += delta
		target = _speech_openness(speech_time - AUDIO_LATENCY)
	# Open fast, close a bit slower, like a real mouth.
	var rate := 18.0 if target > mouth_openness else 9.0
	mouth_openness = lerp(mouth_openness, target, clamp(delta * rate, 0.0, 1.0))
	# Emphasis = how far the voice is above its recent average (stressed syllables).
	loudness_average = lerp(loudness_average, mouth_openness, clamp(delta * 2.0, 0.0, 1.0))
	jaw_modifier.openness = mouth_openness
	jaw_modifier.emphasis = clamp((mouth_openness - loudness_average) * 3.0, 0.0, 1.0) if is_speaking else 0.0


func _speech_openness(t: float) -> float:
	if t < 0.0:
		return 0.0
	if speech_envelope.is_empty():
		# No envelope from the backend: generic talking rhythm.
		var syllables := 0.5 + 0.5 * sin(t * 13.0)
		var phrases := 0.55 + 0.45 * sin(t * 2.1 + 0.7)
		return clamp(syllables * phrases, 0.0, 1.0)
	# Linear interpolation between envelope frames avoids stepped movement.
	var pos := t * envelope_fps
	var i := int(pos)
	if i >= speech_envelope.size():
		return 0.0
	var a := float(speech_envelope[i])
	var b := float(speech_envelope[min(i + 1, speech_envelope.size() - 1)])
	return clamp(lerp(a, b, pos - i), 0.0, 1.0)
