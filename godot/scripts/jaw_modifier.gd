extends SkeletonModifier3D
## Opens Tom's mouth on top of whatever animation is playing.
##
## Skeleton modifiers run after the AnimationPlayer has posed the skeleton,
## so the jaw rotation is not overwritten by breathingL (which keys every
## bone, including the jaw). Set `openness` (0..1) every frame.

## Jaw opening at openness = 1. The model's own talkAD opens it ~20-30°.
@export var max_jaw_degrees: float = 14.0
## The lower lip follows the jaw a little for a rounder mouth shape.
@export var lower_lip_factor: float = 0.45
@export var jaw_bone: String = "c_jaw_skn_014_23"
@export var lower_lip_bone: String = "c_mouthLowLips_skn_016_25"

var openness: float = 0.0

var _jaw_idx: int = -1
var _lip_idx: int = -1


func _ready() -> void:
	var skel := get_skeleton()
	if skel:
		_jaw_idx = skel.find_bone(jaw_bone)
		_lip_idx = skel.find_bone(lower_lip_bone)
	if _jaw_idx < 0:
		push_warning("[Tom] Jaw bone '%s' not found; mouth will not move" % jaw_bone)


func _process_modification_with_delta(_delta: float) -> void:
	var skel := get_skeleton()
	if skel == null or _jaw_idx < 0 or openness <= 0.001:
		return
	# Rotating about the bone's local X axis opens the mouth (measured from talkAD).
	_open(skel, _jaw_idx, max_jaw_degrees * openness)
	if _lip_idx >= 0:
		_open(skel, _lip_idx, max_jaw_degrees * lower_lip_factor * openness)


func _open(skel: Skeleton3D, bone: int, degrees: float) -> void:
	var pose := skel.get_bone_pose_rotation(bone)
	skel.set_bone_pose_rotation(bone, pose * Quaternion(Vector3.RIGHT, deg_to_rad(degrees)))
