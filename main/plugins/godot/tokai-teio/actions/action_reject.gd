# action_reject.gd — 拒绝动作：耳朵自然微颤 + 双臂在胸前比叉号
#
# 手臂：大臂斜向前下，小臂交叉成叉号
#   Arm_L/R: Z=±75°(向前)  X=-45°(向下)
#   Elbow_L: Z=-90°  Elbow_R: Z=+90°

func play(c: Node3D, on_finish: Callable) -> Tween:
	var sk: Skeleton3D = c._skeleton
	if sk == null:
		var tw := c.create_tween()
		tw.tween_interval(0.01)
		tw.finished.connect(on_finish, CONNECT_ONE_SHOT)
		return tw

	# ── 耳朵骨骼（自然微颤）──────────────────────────────────────────────────
	var ear_bone_names := ["Ear_01_L", "Ear_01_R", "Ear_02_L", "Ear_02_R", "Ear_03_L", "Ear_03_R"]
	var ear_ids:   Array[int]        = []
	var ear_rots:  Array[Quaternion] = []
	var ear_axes:  Array[Vector3]    = []
	var world_ear := Vector3(1.0, 0.0, 0.0)
	for bname in ear_bone_names:
		var bid := sk.find_bone(bname)
		ear_ids.append(bid)
		if bid < 0:
			ear_rots.append(Quaternion.IDENTITY)
			ear_axes.append(world_ear)
			continue
		ear_rots.append(sk.get_bone_rest(bid).basis.get_rotation_quaternion())
		var gr := sk.get_bone_global_rest(bid)
		ear_axes.append((gr.basis.inverse() * world_ear).normalized())
	const EAR_AMPS  := [3.0,  3.0,  1.5,  1.5,  0.8,  0.8]
	const EAR_FREQS := [0.37, 0.41, 0.53, 0.57, 0.61, 0.65]
	const EAR_PHASE := [0.0,  1.1,  0.6,  1.7,  1.2,  2.3]

	# ── 手臂骨骼（叉号）──────────────────────────────────────────────────────
	var arm_bone_names := ["Arm_L", "Arm_R", "Elbow_L", "Elbow_R"]
	var arm_ids:  Array[int]        = []
	var arm_prev: Array[Quaternion] = []

	for bname in arm_bone_names:
		var bid := sk.find_bone(bname)
		arm_ids.append(bid)
		arm_prev.append(sk.get_bone_pose_rotation(bid) if bid >= 0 else Quaternion.IDENTITY)

	var arm_targets: Array[Quaternion] = [
		Quaternion(Vector3(0,0,1), deg_to_rad(-75.0)) * Quaternion(Vector3(1,0,0), deg_to_rad(-45.0)),  # Arm_L
		Quaternion(Vector3(0,0,1), deg_to_rad( 75.0)) * Quaternion(Vector3(1,0,0), deg_to_rad(-45.0)),  # Arm_R
		Quaternion(Vector3(0,0,1), deg_to_rad(-90.0)),  # Elbow_L
		Quaternion(Vector3(0,0,1), deg_to_rad( 90.0)),  # Elbow_R
	]
	const T_ARM_IN := 0.35

	var start_time := Time.get_ticks_msec() * 0.001

	c.register_action_process(func() -> void:
		var t       := Time.get_ticks_msec() * 0.001
		var elapsed := t - start_time
		var arm_blend := minf(elapsed / T_ARM_IN, 1.0)

		for ei in range(ear_ids.size()):
			if ear_ids[ei] >= 0:
				sk.set_bone_pose_rotation(ear_ids[ei],
					ear_rots[ei] * Quaternion(ear_axes[ei],
						deg_to_rad(EAR_AMPS[ei] * sin(t * EAR_FREQS[ei] * TAU + EAR_PHASE[ei]))))

		for ai in range(arm_ids.size()):
			if arm_ids[ai] >= 0:
				sk.set_bone_pose_rotation(arm_ids[ai],
					arm_prev[ai].slerp(arm_targets[ai], arm_blend))
	)

	c.register_action_cleanup(func() -> void:
		for ai in range(arm_ids.size()):
			if arm_ids[ai] >= 0:
				sk.set_bone_pose_rotation(arm_ids[ai], arm_prev[ai])
		for ei in range(ear_ids.size()):
			if ear_ids[ei] >= 0:
				sk.set_bone_pose_rotation(ear_ids[ei], ear_rots[ei])
	)

	var tween := c.create_tween()
	tween.tween_interval(3600.0)
	return tween
