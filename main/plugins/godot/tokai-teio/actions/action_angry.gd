# action_angry.gd — 生气动作：飞机耳 + 双手抱在胸前
#
# 耳朵：安装座旋转 + 向后压平 + 向外展开
#
# 手臂（T_ARM_IN 秒渐入）：
#   Arm_L: Z=-25°(前)  X=-25°(高)  Y=-35°(自转夹紧，若反向则改+35)
#   Arm_R: Z=+25°      X=-25°      Y=+35°
#   Elbow_L/R: IDENTITY（伸直，确认大臂位置后再加弯折）

func play(c: Node3D, on_finish: Callable) -> Tween:
	var sk: Skeleton3D = c._skeleton
	if sk == null:
		var tw := c.create_tween()
		tw.tween_interval(0.01)
		tw.finished.connect(on_finish, CONNECT_ONE_SHOT)
		return tw

	# ── 安装座骨（根部旋转）──────────────────────────────────────────────────
	var seat_names := ["Sp_He_Ear0_L_00", "Sp_He_Ear0_R_00"]
	var seat_ids:   Array[int]        = []
	var seat_rots:  Array[Quaternion] = []
	var seat_axes:  Array[Vector3]    = []
	var world_seat := Vector3(0.0, 1.0, 0.0)

	for bname in seat_names:
		var bid := sk.find_bone(bname)
		seat_ids.append(bid)
		if bid < 0:
			seat_rots.append(Quaternion.IDENTITY)
			seat_axes.append(world_seat)
			continue
		seat_rots.append(sk.get_bone_rest(bid).basis.get_rotation_quaternion())
		var gr := sk.get_bone_global_rest(bid)
		seat_axes.append((gr.basis.inverse() * world_seat).normalized())

	const SEAT_ANGS := [35.0, -35.0]

	# ── 耳朵本体骨（弯折）──────────────────────────────────────────────────
	var ear_bone_names := [
		"Ear_01_L", "Ear_01_R",
		"Ear_02_L", "Ear_02_R",
		"Ear_03_L", "Ear_03_R",
	]
	var ear_ids:     Array[int]        = []
	var ear_rots:    Array[Quaternion] = []
	var press_axes:  Array[Vector3]    = []
	var spread_axes: Array[Vector3]    = []
	var world_press  := Vector3(1.0, 0.0, 0.0)
	var world_spread := Vector3(0.0, 1.0, 0.0)

	for bname in ear_bone_names:
		var bid := sk.find_bone(bname)
		ear_ids.append(bid)
		if bid < 0:
			ear_rots.append(Quaternion.IDENTITY)
			press_axes.append(world_press)
			spread_axes.append(world_spread)
			continue
		ear_rots.append(sk.get_bone_rest(bid).basis.get_rotation_quaternion())
		var gr := sk.get_bone_global_rest(bid)
		press_axes.append((gr.basis.inverse() * world_press).normalized())
		spread_axes.append((gr.basis.inverse() * world_spread).normalized())

	const PRESS_ANGS  := [-50.0, -50.0, -15.0, -15.0,  -8.0,  -8.0]
	const SPREAD_ANGS := [ 25.0, -25.0,   8.0,  -8.0,   4.0,  -4.0]

	const T_PRESS      := 0.25
	const TREMBLE_AMP  := 1.2
	const TREMBLE_FREQ := 9.0

	# ── 手臂骨骼（抱胸）──────────────────────────────────────────────────────
	var arm_bone_names := ["Arm_L", "Arm_R", "Elbow_L", "Elbow_R"]
	var arm_ids:  Array[int]        = []
	var arm_prev: Array[Quaternion] = []

	for bname in arm_bone_names:
		var bid := sk.find_bone(bname)
		arm_ids.append(bid)
		arm_prev.append(sk.get_bone_pose_rotation(bid) if bid >= 0 else Quaternion.IDENTITY)

	var arm_targets: Array[Quaternion] = [
		Quaternion(Vector3(0,0,1), deg_to_rad(-25.0)) * Quaternion(Vector3(1,0,0), deg_to_rad(-67.0)),  # Arm_L
		Quaternion(Vector3(0,0,1), deg_to_rad( 55.0)) * Quaternion(Vector3(1,0,0), deg_to_rad(-50.0)),  # Arm_R
		Quaternion(Vector3(0,0,1), deg_to_rad(-125.0)) * Quaternion(Vector3(1,0,0), deg_to_rad(-50.0)),  # Elbow_L
		Quaternion(Vector3(0,0,1), deg_to_rad( 115.0)) * Quaternion(Vector3(1,0,0), deg_to_rad(-50.0)),  # Elbow_R
	]
	const T_ARM_IN := 0.3  # 手臂渐入时长（与耳朵基本同步）

	# ── 手指骨骼 ──────────────────────────────────────────────────────────────
	# 左手半握：四指各节弯曲约50°，拇指略收
	# 右手轻握：手腕旋转90° + 四指各节弯曲约20°
	var finger_bone_names := [
		"Wrist_L",
		"Index_01_L",  "Index_02_L",  "Index_03_L",
		"Middle_01_L", "Middle_02_L", "Middle_03_L",
		"Ring_01_L",   "Ring_02_L",   "Ring_03_L",
		"Pinky_01_L",  "Pinky_02_L",  "Pinky_03_L",
		"Thumb_01_L",  "Thumb_02_L",  "Thumb_03_L",
		"Wrist_R",
		"Index_01_R",  "Index_02_R",  "Index_03_R",
		"Middle_01_R", "Middle_02_R", "Middle_03_R",
		"Ring_01_R",   "Ring_02_R",   "Ring_03_R",
		"Pinky_01_R",  "Pinky_02_R",  "Pinky_03_R",
		"Thumb_01_R",  "Thumb_02_R",  "Thumb_03_R",
	]
	var finger_ids:  Array[int]        = []
	var finger_prev: Array[Quaternion] = []

	for bname in finger_bone_names:
		var bid := sk.find_bone(bname)
		finger_ids.append(bid)
		finger_prev.append(sk.get_bone_pose_rotation(bid) if bid >= 0 else Quaternion.IDENTITY)

	# 左手半握目标（Z轴弯曲，正值=握拳方向，可能需要改负值）
	const HALF_GRIP  := 50.0  # 四指弯曲幅度
	const THUMB_L    := 30.0  # 拇指弯曲
	# 右手轻握目标
	const WRIST_R_ROT := 90.0  # 手腕旋转（Z轴，若方向不对改负值）
	const LIGHT_GRIP  := 20.0  # 四指弯曲幅度
	const THUMB_R     := 15.0  # 拇指弯曲

	var finger_targets: Array[Quaternion] = [
		Quaternion(Vector3(1,0,0), deg_to_rad(-15.0)),  # Wrist_L（略微下压）
		# 左手四指半握
		Quaternion(Vector3(0,0,1), deg_to_rad(HALF_GRIP)),   # Index_01_L
		Quaternion(Vector3(0,0,1), deg_to_rad(HALF_GRIP)),   # Index_02_L
		Quaternion(Vector3(0,0,1), deg_to_rad(HALF_GRIP)),   # Index_03_L
		Quaternion(Vector3(0,0,1), deg_to_rad(HALF_GRIP)),   # Middle_01_L
		Quaternion(Vector3(0,0,1), deg_to_rad(HALF_GRIP)),   # Middle_02_L
		Quaternion(Vector3(0,0,1), deg_to_rad(HALF_GRIP)),   # Middle_03_L
		Quaternion(Vector3(0,0,1), deg_to_rad(HALF_GRIP)),   # Ring_01_L
		Quaternion(Vector3(0,0,1), deg_to_rad(HALF_GRIP)),   # Ring_02_L
		Quaternion(Vector3(0,0,1), deg_to_rad(HALF_GRIP)),   # Ring_03_L
		Quaternion(Vector3(0,0,1), deg_to_rad(HALF_GRIP)),   # Pinky_01_L
		Quaternion(Vector3(0,0,1), deg_to_rad(HALF_GRIP)),   # Pinky_02_L
		Quaternion(Vector3(0,0,1), deg_to_rad(HALF_GRIP)),   # Pinky_03_L
		Quaternion.IDENTITY,  # Thumb_01_L
		Quaternion.IDENTITY,  # Thumb_02_L
		Quaternion.IDENTITY,  # Thumb_03_L
		# 右手腕旋转90°
		Quaternion(Vector3(0,0,1), deg_to_rad(WRIST_R_ROT)), # Wrist_R
		# 右手轻握
		Quaternion(Vector3(0,0,1), deg_to_rad(LIGHT_GRIP)),  # Index_01_R
		Quaternion(Vector3(0,0,1), deg_to_rad(LIGHT_GRIP)),  # Index_02_R
		Quaternion(Vector3(0,0,1), deg_to_rad(LIGHT_GRIP)),  # Index_03_R
		Quaternion(Vector3(0,0,1), deg_to_rad(LIGHT_GRIP)),  # Middle_01_R
		Quaternion(Vector3(0,0,1), deg_to_rad(LIGHT_GRIP)),  # Middle_02_R
		Quaternion(Vector3(0,0,1), deg_to_rad(LIGHT_GRIP)),  # Middle_03_R
		Quaternion(Vector3(0,0,1), deg_to_rad(LIGHT_GRIP)),  # Ring_01_R
		Quaternion(Vector3(0,0,1), deg_to_rad(LIGHT_GRIP)),  # Ring_02_R
		Quaternion(Vector3(0,0,1), deg_to_rad(LIGHT_GRIP)),  # Ring_03_R
		Quaternion(Vector3(0,0,1), deg_to_rad(LIGHT_GRIP)),  # Pinky_01_R
		Quaternion(Vector3(0,0,1), deg_to_rad(LIGHT_GRIP)),  # Pinky_02_R
		Quaternion(Vector3(0,0,1), deg_to_rad(LIGHT_GRIP)),  # Pinky_03_R
		Quaternion.IDENTITY,  # Thumb_01_R
		Quaternion.IDENTITY,  # Thumb_02_R
		Quaternion.IDENTITY,  # Thumb_03_R
	]

	var start_time := Time.get_ticks_msec() * 0.001

	c.register_action_process(func() -> void:
		var t:      float = Time.get_ticks_msec() * 0.001
		var elapsed: float = t - start_time
		var blend:  float = minf(elapsed / T_PRESS, 1.0)
		var arm_blend: float = minf(elapsed / T_ARM_IN, 1.0)

		# 安装座扭转
		for si in range(seat_ids.size()):
			if seat_ids[si] >= 0:
				sk.set_bone_pose_rotation(seat_ids[si],
					seat_rots[si] * Quaternion(seat_axes[si], deg_to_rad(SEAT_ANGS[si] * blend)))

		# 耳朵本体弯折 + 颤抖
		for ei in range(ear_ids.size()):
			if ear_ids[ei] >= 0:
				var tremble: float   = TREMBLE_AMP * sin(t * TREMBLE_FREQ * TAU + float(ei) * 0.8) * blend
				var q_press: Quaternion  = Quaternion(press_axes[ei],
					deg_to_rad(PRESS_ANGS[ei] * blend + tremble))
				var q_spread: Quaternion = Quaternion(spread_axes[ei],
					deg_to_rad(SPREAD_ANGS[ei] * blend))
				sk.set_bone_pose_rotation(ear_ids[ei], ear_rots[ei] * q_press * q_spread)

		# 手臂抱胸（渐入）
		for ai in range(arm_ids.size()):
			if arm_ids[ai] >= 0:
				sk.set_bone_pose_rotation(arm_ids[ai],
					arm_prev[ai].slerp(arm_targets[ai], arm_blend))

		# 手指握姿（渐入）
		for fi in range(finger_ids.size()):
			if finger_ids[fi] >= 0:
				sk.set_bone_pose_rotation(finger_ids[fi],
					finger_prev[fi].slerp(finger_targets[fi], arm_blend))
	)

	c.register_action_cleanup(func() -> void:
		for ai in range(arm_ids.size()):
			if arm_ids[ai] >= 0:
				sk.set_bone_pose_rotation(arm_ids[ai], arm_prev[ai])
		for fi in range(finger_ids.size()):
			if finger_ids[fi] >= 0:
				sk.set_bone_pose_rotation(finger_ids[fi], finger_prev[fi])
		for si in range(seat_ids.size()):
			if seat_ids[si] >= 0:
				sk.set_bone_pose_rotation(seat_ids[si], seat_rots[si])
		for ei in range(ear_ids.size()):
			if ear_ids[ei] >= 0:
				sk.set_bone_pose_rotation(ear_ids[ei], ear_rots[ei])
	)

	var tween := c.create_tween()
	tween.tween_interval(3600.0)
	return tween
