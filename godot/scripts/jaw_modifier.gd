extends SkeletonModifier3D
## Lip sync for Tom.
##
## Blends only the mouth bones (jaw, chin, lips, mouth corners, teeth) towards
## the model's own talk animation, weighted by how loud Tom's voice is right
## now. The artist-made mouth shapes look far more natural than rotating the
## jaw alone. Skeleton modifiers run after the AnimationPlayer, so the idle
## animation cannot overwrite the result.

const MOUTH_BONE_WORDS := ["jaw", "chin", "mouth", "lip", "teeth", "tongue"]

## Mouth shapes are taken from this animation (see set_talk_animation).
var talk_animation: Animation
## 0..1, how open the mouth should be (set every frame from the speech envelope).
var openness: float = 0.0
## 0..1 short loudness peaks; drives small head nods on stressed syllables.
var emphasis: float = 0.0

@export var head_bone: String = "c_head_00_skn_012_21"
@export var head_nod_degrees: float = 3.0
## How much of the talk pose is used at full loudness.
@export var max_blend: float = 0.8

var _phase: float = 0.0
var _range_start: float = 0.0   # part of the talk animation where the mouth moves
var _range_end: float = 0.0
var _bones: Array = []     # [{idx, rot, pos}] mouth bones with their tracks
var _head_idx: int = -1
var _nod: float = 0.0


func set_talk_animation(anim: Animation) -> void:
	if anim == null or anim == talk_animation:
		return
	talk_animation = anim
	_bones.clear()
	var skel := get_skeleton()
	if skel == null:
		return
	var tracks := {}
	for t in anim.get_track_count():
		var bone := String(anim.track_get_path(t)).get_slice(":", 1)
		if not tracks.has(bone):
			tracks[bone] = {"rot": -1, "pos": -1}
		match anim.track_get_type(t):
			Animation.TYPE_ROTATION_3D:
				tracks[bone]["rot"] = t
			Animation.TYPE_POSITION_3D:
				tracks[bone]["pos"] = t
	for bone in tracks:
		var lower := String(bone).to_lower()
		for word in MOUTH_BONE_WORDS:
			if word in lower:
				var idx := skel.find_bone(bone)
				if idx >= 0:
					_bones.append({"idx": idx, "rot": tracks[bone]["rot"], "pos": tracks[bone]["pos"]})
				break
	_head_idx = skel.find_bone(head_bone)
	# Loop only over the keyed span; outside it the mouth would freeze in one shape.
	_range_start = anim.length
	_range_end = 0.0
	for b in _bones:
		for key in ["rot", "pos"]:
			var t: int = b[key]
			if t >= 0 and anim.track_get_key_count(t) > 1:
				_range_start = minf(_range_start, anim.track_get_key_time(t, 0))
				_range_end = maxf(_range_end, anim.track_get_key_time(t, anim.track_get_key_count(t) - 1))
	if _range_end - _range_start < 0.2:
		_range_start = 0.0
		_range_end = anim.length
	_phase = _range_start
	if _bones.is_empty():
		push_warning("[Tom] No mouth bones found in %s; lip sync disabled" % anim.resource_name)


## Start a new line at a random point so sentences don't all begin alike.
func restart() -> void:
	if _range_end > _range_start:
		_phase = randf_range(_range_start, _range_end)


func _process_modification_with_delta(delta: float) -> void:
	var skel := get_skeleton()
	if skel == null or talk_animation == null:
		return

	# Walk through the talk animation faster when Tom speaks louder, so the
	# mouth shapes change with the syllables instead of looping mechanically.
	if openness > 0.02:
		var span := _range_end - _range_start
		_phase = _range_start + fmod(_phase - _range_start + delta * (0.5 + 0.9 * openness), span)

	var w := clampf(openness, 0.0, 1.0) * max_blend
	if w > 0.001:
		for b in _bones:
			var idx: int = b["idx"]
			if b["rot"] >= 0:
				var target: Quaternion = talk_animation.rotation_track_interpolate(b["rot"], _phase)
				skel.set_bone_pose_rotation(idx, skel.get_bone_pose_rotation(idx).slerp(target, w))
			if b["pos"] >= 0:
				var target_pos: Vector3 = talk_animation.position_track_interpolate(b["pos"], _phase)
				skel.set_bone_pose_position(idx, skel.get_bone_pose_position(idx).lerp(target_pos, w))

	# Small nod that follows stressed syllables, then settles.
	_nod = lerpf(_nod, emphasis, clampf(delta * 10.0, 0.0, 1.0))
	if _head_idx >= 0 and _nod > 0.001:
		var pose := skel.get_bone_pose_rotation(_head_idx)
		skel.set_bone_pose_rotation(_head_idx, pose * Quaternion(Vector3.RIGHT, deg_to_rad(-head_nod_degrees * _nod)))
