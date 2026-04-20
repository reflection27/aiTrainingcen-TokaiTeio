# action_smile.gd — 微笑动作：尾巴轻柔摇动（与 happy 同波形，幅度约 70%、周期略长）
#
# 波形与 happy 完全相同，只调：
#   PERIOD 2.0 → 2.4（稍慢，更从容）
#   AMPLITUDES 缩小到 happy 的约 70%

func play(c: Node3D, on_finish: Callable) -> Tween:
	var sk: Skeleton3D = c._skeleton
	if sk == null:
		var tw := c.create_tween()
		tw.tween_interval(0.01)
		tw.finished.connect(on_finish, CONNECT_ONE_SHOT)
		return tw

	# ── 尾巴骨骼 ─────────────────────────────────────────────────────────────
	var bone_names := [
		"Sp_Hi_Tail0_B_00", "Sp_Hi_Tail0_B_01", "Sp_Hi_Tail0_B_02",
		"Sp_Hi_Tail0_B_03", "Sp_Hi_Tail0_B_04",
	]
	var bone_ids:  Array[int]        = []
	var base_rots: Array[Quaternion] = []
	var wag_axes:  Array[Vector3]    = []
	var world_wag := Vector3(0.0, 0.0, 1.0)

	for bname in bone_names:
		var bid := sk.find_bone(bname)
		bone_ids.append(bid)
		if bid < 0:
			base_rots.append(Quaternion.IDENTITY)
			wag_axes.append(world_wag)
			continue
		base_rots.append(sk.get_bone_rest(bid).basis.get_rotation_quaternion())
		var gr := sk.get_bone_global_rest(bid)
		wag_axes.append((gr.basis.inverse() * world_wag).normalized())

	const PERIOD   := 2.4                                # happy(2.0) より稍慢
	const T_SWING  := 0.510                              # 4×T_SWING + 2×T_HOLD = 2.4
	const T_HOLD   := 0.18
	const BONE_DLY := 0.035
	const AMPLITUDES := [14.0, 20.0, 27.0, 34.0, 41.0] # happy 的约 70%

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

	# 波形节点时间
	const TP1 := T_SWING
	const TP2 := T_SWING + T_HOLD
	const TP3 := T_SWING * 2.0 + T_HOLD
	const TP4 := T_SWING * 3.0 + T_HOLD
	const TP5 := T_SWING * 3.0 + T_HOLD * 2.0

	var _wave := func(tp: float) -> float:
		if tp < TP1:
			return sin(tp / T_SWING * PI * 0.5)
		elif tp < TP2:
			return 1.0
		elif tp < TP3:
			return cos((tp - TP2) / T_SWING * PI * 0.5)
		elif tp < TP4:
			return -sin((tp - TP3) / T_SWING * PI * 0.5)
		elif tp < TP5:
			return -1.0
		else:
			return -cos((tp - TP5) / T_SWING * PI * 0.5)

	c.register_action_process(func() -> void:
		var now := Time.get_ticks_msec() * 0.001
		for i in range(bone_ids.size()):
			if bone_ids[i] < 0:
				continue
			var tp: float = fmod(now - float(i) * BONE_DLY, PERIOD)
			if tp < 0.0:
				tp += PERIOD
			var wag: float = _wave.call(tp) * AMPLITUDES[i]
			sk.set_bone_pose_rotation(bone_ids[i],
				base_rots[i] * Quaternion(wag_axes[i], deg_to_rad(wag)))
		for ei in range(ear_ids.size()):
			if ear_ids[ei] >= 0:
				sk.set_bone_pose_rotation(ear_ids[ei],
					ear_rots[ei] * Quaternion(ear_axes[ei],
						deg_to_rad(EAR_AMPS[ei] * sin(now * EAR_FREQS[ei] * TAU + EAR_PHASE[ei]))))
	)

	c.register_action_cleanup(func() -> void:
		for i in range(bone_ids.size()):
			if bone_ids[i] >= 0:
				sk.set_bone_pose_rotation(bone_ids[i], base_rots[i])
		for ei in range(ear_ids.size()):
			if ear_ids[ei] >= 0:
				sk.set_bone_pose_rotation(ear_ids[ei], ear_rots[ei])
	)

	var tween := c.create_tween()
	tween.tween_interval(3600.0)
	return tween
