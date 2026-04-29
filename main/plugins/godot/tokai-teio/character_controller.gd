extends Node3D

## 角色动画控制器
## - 手臂放下（骨骼旋转）
## - 程序化 idle/talking 摇摆
## - 表情预设（happy/sad/angry/surprised/smug/excited/normal）
## - 说话时自动口型动画

enum State { IDLE, TALKING, WAVE }

var _state: State = State.IDLE
var _base_y: float = 0.0
var _base_rot_y: float = 0.0  # 外部设置的 Y 轴基准朝向（弧度），摇摆叠加在此偏移上
var _is_waving: bool = false
var _wave_tween: Tween = null
var _expr_tween: Tween = null
var _action_tween: Tween = null
var _action_process_cb: Callable = Callable()   # 动作每帧回调
var _action_cleanup_cb: Callable = Callable()   # 动作结束时归零回调

var _skeleton: Skeleton3D = null
var _mesh_instances: Array = []
var _eye_material: ShaderMaterial = null  # 眼睛高光 Shader 材质

# 失去高光的表情
const DEAD_EYE_PRESETS: Array = ["angry", "sad"]

# 当前激活的 blend shape 目标值
var _active_shapes: Dictionary = {}
# 所有曾经改动过的 blend shape，切换时全部归零防止残留
var _all_touched_shapes: Dictionary = {}

# ── 表情预设（按需扩充）────────────────────────────────────────────────────────
# 格式：preset_name → { blend_shape_name: value }
# 每次切换会先把上一组表情 Tween 归零，再淡入新表情
const EXPRESSIONS: Dictionary = {
	"normal": {},
	"happy": {
		"Eye_5_R(WaraiA)[M_Face]": 0.85,
		"Eye_5_L(WaraiA)[M_Face]": 0.85,
		"EyeBrow_1_R(WaraiA)[M_Face]": 0.8,
		"EyeBrow_1_L(WaraiA)[M_Face]": 0.8,
		"EyeBrow_1_R(WaraiA)[M_Mayu]": 0.8,
		"EyeBrow_1_L(WaraiA)[M_Mayu]": 0.8,
		"Mouth_4_0(WaraiA)[M_Face]": 0.85,
	},
	"smile": {
		"Eye_6_R(WaraiB)[M_Face]": 0.75,
		"Eye_6_L(WaraiB)[M_Face]": 0.75,
		"EyeBrow_2_R(WaraiB)[M_Face]": 0.6,
		"EyeBrow_2_L(WaraiB)[M_Face]": 0.6,
		"EyeBrow_2_R(WaraiB)[M_Mayu]": 0.6,
		"EyeBrow_2_L(WaraiB)[M_Mayu]": 0.6,
		"Mouth_5_0(WaraiB)[M_Face]": 0.8,
	},
	"angry": {
		"Eye_9_R(IkariA)[M_Face]": 0.8,
		"Eye_9_L(IkariA)[M_Face]": 0.8,
		"EyeBrow_5_R(IkariA)[M_Face]": 0.8,
		"EyeBrow_5_L(IkariA)[M_Face]": 0.8,
		"EyeBrow_5_R(IkariA)[M_Mayu]": 0.8,
		"EyeBrow_5_L(IkariA)[M_Mayu]": 0.8,
		"Mouth_9_0(IkariA)[M_Face]": 0.7,
	},
	"sad": {
		"Eye_10_R(KanasiA)[M_Face]": 0.8,
		"Eye_10_L(KanasiA)[M_Face]": 0.8,
		"EyeBrow_6_R(KanasiA)[M_Face]": 0.8,
		"EyeBrow_6_L(KanasiA)[M_Face]": 0.8,
		"EyeBrow_6_R(KanasiA)[M_Mayu]": 0.8,
		"EyeBrow_6_L(KanasiA)[M_Mayu]": 0.8,
		"Mouth_11_0(KanasiA)[M_Face]": 0.7,
	},
	"surprised": {
		"Eye_12_R(OdorokiA)[M_Face]": 1.0,
		"Eye_12_L(OdorokiA)[M_Face]": 1.0,
		"EyeBrow_9_R(OdorokiA)[M_Face]": 0.9,
		"EyeBrow_9_L(OdorokiA)[M_Face]": 0.9,
		"EyeBrow_9_R(OdorokiA)[M_Mayu]": 0.9,
		"EyeBrow_9_L(OdorokiA)[M_Mayu]": 0.9,
		"Mouth_14_0(OdorokiA)[M_Face]": 0.85,
	},
	"smug": {
		"EyeBrow_7_R(DoyaA)[M_Face]": 0.8,
		"EyeBrow_7_L(DoyaA)[M_Face]": 0.8,
		"EyeBrow_7_R(DoyaA)[M_Mayu]": 0.8,
		"EyeBrow_7_L(DoyaA)[M_Mayu]": 0.8,
		"Mouth_12_0(DoyaA)[M_Face]": 0.85,
	},
	"dere": {
		"Eye_11_R(DereA)[M_Face]": 0.85,
		"Eye_11_L(DereA)[M_Face]": 0.85,
		"EyeBrow_8_R(DereA)[M_Face]": 0.6,
		"EyeBrow_8_L(DereA)[M_Face]": 0.6,
		"EyeBrow_8_R(DereA)[M_Mayu]": 0.6,
		"EyeBrow_8_L(DereA)[M_Mayu]": 0.6,
		"Mouth_13_0(DereA)[M_Face]": 0.75,
	},
	"excited": {
		"Eye_18_R(RunA)[M_Face]": 0.8,
		"Eye_18_L(RunA)[M_Face]": 0.8,
		"EyeBrow_15_R(RunA)[M_Face]": 0.75,
		"EyeBrow_15_L(RunA)[M_Face]": 0.75,
		"EyeBrow_15_R(RunA)[M_Mayu]": 0.75,
		"EyeBrow_15_L(RunA)[M_Mayu]": 0.75,
		"Mouth_39_0(RunA)[M_Face]": 0.8,
	},
}

# ── 心情动作映射 ───────────────────────────────────────────────────────────────
# 每个脚本暴露 static func play(c: Node3D, on_finish: Callable) -> Tween
const ACTION_MAP: Dictionary = {
	"normal":    preload("res://actions/action_normal.gd"),
	"happy":     preload("res://actions/action_happy.gd"),
	"smile":     preload("res://actions/action_smile.gd"),
	"angry":     preload("res://actions/action_angry.gd"),
	"sad":       preload("res://actions/action_sad.gd"),
	"surprised": preload("res://actions/action_surprised.gd"),
	"smug":      preload("res://actions/action_smug.gd"),
	"dere":      preload("res://actions/action_dere.gd"),
	"excited":   preload("res://actions/action_excited.gd"),
	"reject":    preload("res://actions/action_reject.gd"),
	"cheer":     preload("res://actions/action_cheer.gd"),
}

# 说话口型循环（小→大→下一音→…）
const TALK_SHAPES: Array = [
	"Mouth_23_0(TalkA_A_S)[M_Face]",
	"Mouth_24_0(TalkA_A_L)[M_Face]",
	"Mouth_25_0(TalkA_I_S)[M_Face]",
	"Mouth_27_0(TalkA_U_S)[M_Face]",
	"Mouth_29_0(TalkA_E_S)[M_Face]",
	"Mouth_31_0(TalkA_O_S)[M_Face]",
]
var _talk_shape_idx: int = 0
var _talk_timer: float = 0.0
const TALK_INTERVAL: float = 0.12  # 每帧口型持续秒数


func _ready() -> void:
	_base_y = position.y
	await get_tree().process_frame
	_discover_nodes(self)
	_apply_arm_pose()
	_reset_all_expression_shapes()
	await get_tree().create_timer(0.5).timeout
	_do_wave()


func _reset_all_expression_shapes() -> void:
	for preset in EXPRESSIONS.values():
		for shape in preset.keys():
			_set_raw_blend_shape(shape, 0.0)
			_all_touched_shapes[shape] = true


# ── 节点发现 ───────────────────────────────────────────────────────────────────

func _discover_nodes(node: Node) -> void:
	for child in node.get_children():
		if child is Skeleton3D and _skeleton == null:
			_skeleton = child
		if child is MeshInstance3D:
			_mesh_instances.append(child)
			_try_find_eye_material(child as MeshInstance3D)
		_discover_nodes(child)


func _try_find_eye_material(mi: MeshInstance3D) -> void:
	if _eye_material != null:
		return
	# 眼睛在 surface 3，且该 mesh 共 7 个 surface
	if mi.mesh == null or mi.mesh.get_surface_count() != 7:
		return
	var shader := load("res://shaders/eye_highlight.gdshader") as Shader
	if shader == null:
		push_warning("[EyeHL] 找不到 res://shaders/eye_highlight.gdshader")
		return
	# 取原材质的贴图
	var orig := mi.mesh.surface_get_material(3)
	var eye_tex: Texture2D = null
	if orig is StandardMaterial3D:
		eye_tex = (orig as StandardMaterial3D).albedo_texture
	if eye_tex == null:
		push_warning("[EyeHL] 无法获取眼睛贴图，放弃挂载")
		return
	var mat := ShaderMaterial.new()
	mat.shader = shader
	mat.set_shader_parameter("texture_albedo", eye_tex)
	mat.set_shader_parameter("hl1_uv",       Vector2(0.81, 0.38))
	mat.set_shader_parameter("hl1_radius",   0.2)
	mat.set_shader_parameter("hl1_strength", 0.85)
	mat.set_shader_parameter("hl2_uv",       Vector2(0.16, 0.78))
	mat.set_shader_parameter("hl2_radius",   0.035)
	mat.set_shader_parameter("hl2_strength", 0.40)
	mat.set_shader_parameter("highlight_alpha", 1.0)
	mi.set_surface_override_material(3, mat)
	_eye_material = mat
	print("[EyeHL] 眼睛高光 Shader 已自动挂载到 %s surface 3" % mi.name)


# ── 手臂放下 ───────────────────────────────────────────────────────────────────
# 如果效果不对，调整 ARM_DOWN_ANGLE（正值=左臂向内转，负值=向外）

# 轴角方式，直接调数值调整姿态
# Z 轴：左臂正角 = 向后，负角 = 向前；右臂镜像
# Y 轴：左臂正角 = 向前，负角 = 向后（水平旋转）
# X 轴：正角 = 向上，负角 = 向下
const ARM_Z := 0.0    # Z 轴：正 = 向后，负 = 向前（0 = T-pose 水平）
const ARM_Y := 0.0    # Y 轴：沿手臂自转（通常不需要）
const ARM_X := -55.0  # X 轴：负 = 向下，正 = 向上

# 挥手动画专用
const WAVE_ARM_Y   := 60.0   # 上臂 Y 轴侧举角度
const WAVE_ELBOW_Z := 150.0  # 肘部 Z 轴弯曲角度


func _apply_arm_pose() -> void:
	if _skeleton == null:
		push_warning("[ArmPose] Skeleton3D not found")
		return
	var arm_l: int = _skeleton.find_bone("Arm_L")
	var arm_r: int = _skeleton.find_bone("Arm_R")

	if arm_l >= 0:
		var q := (Quaternion(Vector3(0, 0, 1), deg_to_rad(ARM_Z))
				* Quaternion(Vector3(0, 1, 0), deg_to_rad(ARM_Y))
				* Quaternion(Vector3(1, 0, 0), deg_to_rad(ARM_X)))
		_skeleton.set_bone_pose_rotation(arm_l, q)
	if arm_r >= 0:
		var q := (Quaternion(Vector3(0, 0, 1), deg_to_rad(-ARM_Z))
				* Quaternion(Vector3(0, 1, 0), deg_to_rad(-ARM_Y))
				* Quaternion(Vector3(1, 0, 0), deg_to_rad(ARM_X)))  # X 轴两侧同号
		_skeleton.set_bone_pose_rotation(arm_r, q)

	print("[ArmPose] Z=%.1f Y=%.1f X=%.1f" % [ARM_Z, ARM_Y, ARM_X])


# ── _process：程序化动画 + 口型 ────────────────────────────────────────────────

func _process(delta: float) -> void:
	if _is_waving:
		return
	var t := Time.get_ticks_msec() * 0.001
	match _state:
		State.IDLE:
			position.y = _base_y + sin(t * 1.6) * 0.01
			rotation.y = _base_rot_y + sin(t * 0.7) * deg_to_rad(2.5)
			rotation.x = sin(t * 1.25 + 1.0) * deg_to_rad(0.5)
		State.TALKING:
			position.y = _base_y + sin(t * 2.2) * 0.013
			rotation.y = _base_rot_y + sin(t * 1.4) * deg_to_rad(3.5)
			rotation.x = sin(t * 1.8 + 0.5) * deg_to_rad(1.2)
			_update_lip_sync(delta)
	if _action_process_cb.is_valid():
		_action_process_cb.call()


func _update_lip_sync(delta: float) -> void:
	_talk_timer -= delta
	if _talk_timer > 0.0:
		return
	_talk_timer = TALK_INTERVAL
	# 关掉上一个口型
	var prev: String = TALK_SHAPES[_talk_shape_idx]
	_set_raw_blend_shape(prev, 0.0)
	# 随机跳到下一个口型（避免单调）
	_talk_shape_idx = randi() % TALK_SHAPES.size()
	_set_raw_blend_shape(TALK_SHAPES[_talk_shape_idx], randf_range(0.5, 1.0))


func _stop_lip_sync() -> void:
	for shape in TALK_SHAPES:
		_set_raw_blend_shape(shape, 0.0)
	_talk_timer = 0.0


# ── 公共接口 ───────────────────────────────────────────────────────────────────

func _suppress_expression_mouth(suppress: bool) -> void:
	for shape in _active_shapes.keys():
		if shape.begins_with("Mouth_"):
			var target: float = 0.0 if suppress else _active_shapes[shape]
			_set_raw_blend_shape(shape, target)


func set_state(state_name: String) -> void:
	match state_name:
		"idle":
			if _state == State.TALKING:
				_stop_lip_sync()
				_suppress_expression_mouth(false)
			_state = State.IDLE
		"talking":
			if _state != State.TALKING:
				_suppress_expression_mouth(true)
			_state = State.TALKING
		"wave":
			if not _is_waving:
				_do_wave()
			return
	if _is_waving:
		if _wave_tween:
			_wave_tween.kill()
		_is_waving = false
		rotation.z = 0.0


func set_expression(preset_name: String, duration: float = 0.3) -> bool:
	"""按预设名设置表情，支持淡入淡出"""
	if not preset_name in EXPRESSIONS:
		push_warning("[Expression] unknown preset: " + preset_name)
		return false
	if _expr_tween:
		_expr_tween.kill()
	_expr_tween = create_tween().set_parallel(true)
	# 淡出所有曾经动过的 shape（防止中断后残留）
	var new_shapes: Dictionary = EXPRESSIONS[preset_name]
	for shape in _all_touched_shapes.keys():
		if shape not in new_shapes:
			_expr_tween.tween_method(_make_shape_setter(shape), _get_blend_shape_value(shape), 0.0, duration)
	# 淡入新表情
	for shape in new_shapes.keys():
		var target: float = new_shapes[shape]
		_expr_tween.tween_method(_make_shape_setter(shape), _get_blend_shape_value(shape), target, duration)
		_all_touched_shapes[shape] = true
	_active_shapes = new_shapes.duplicate()

	# 高光：生气/悲伤时淡出，其他表情淡回
	if _eye_material:
		var target_alpha := 0.0 if preset_name in DEAD_EYE_PRESETS else 1.0
		_expr_tween.tween_method(
			func(v: float) -> void: _eye_material.set_shader_parameter("highlight_alpha", v),
			_eye_material.get_shader_parameter("highlight_alpha"),
			target_alpha,
			duration
		)

	return true


func set_blend_shape(mesh_name: String, shape_name: String, value: float) -> bool:
	"""直接设置单个 BlendShape"""
	return _set_raw_blend_shape(shape_name, value, mesh_name)


func set_eye_highlight_param(param: String, value: float) -> void:
	if _eye_material == null:
		push_warning("[EyeHL] 材质未初始化")
		return
	match param:
		"hl1_uv_x":
			var cur := _eye_material.get_shader_parameter("hl1_uv") as Vector2
			_eye_material.set_shader_parameter("hl1_uv", Vector2(value, cur.y))
		"hl1_uv_y":
			var cur := _eye_material.get_shader_parameter("hl1_uv") as Vector2
			_eye_material.set_shader_parameter("hl1_uv", Vector2(cur.x, value))
		"hl2_uv_x":
			var cur := _eye_material.get_shader_parameter("hl2_uv") as Vector2
			_eye_material.set_shader_parameter("hl2_uv", Vector2(value, cur.y))
		"hl2_uv_y":
			var cur := _eye_material.get_shader_parameter("hl2_uv") as Vector2
			_eye_material.set_shader_parameter("hl2_uv", Vector2(cur.x, value))
		_:
			_eye_material.set_shader_parameter(param, value)


func play_action(expr_name: String) -> void:
	"""播放与表情对应的肢体动作，动作结束后自动清理"""
	if _action_tween:
		_action_tween.kill()
		_action_tween = null
	if _action_cleanup_cb.is_valid():
		_action_cleanup_cb.call()
	_action_process_cb = Callable()
	_action_cleanup_cb = Callable()
	if not expr_name in ACTION_MAP:
		push_warning("[Action] unknown action: " + expr_name)
		return
	_action_tween = (ACTION_MAP[expr_name] as GDScript).new().play(self, func() -> void: _action_tween = null)


func register_action_process(cb: Callable) -> void:
	"""供动作文件注册每帧回调，用于持续性动画（如尾巴摇动）"""
	_action_process_cb = cb


func register_action_cleanup(cb: Callable) -> void:
	"""供动作文件注册清理回调，切换动作时自动调用以归零骨骼"""
	_action_cleanup_cb = cb


func reset_pose() -> void:
	set_expression("normal")
	_apply_arm_pose()


## 调参用：把尾巴各骨骼按世界 X 轴旋转 angle_deg 度（正值向后下垂）
## 通过 TCP {"cmd":"tail_droop","angle":XX} 调用
func set_tail_droop(angle_deg: float) -> void:
	if _skeleton == null:
		return
	var bone_names := [
		"Sp_Hi_Tail0_B_00",
		"Sp_Hi_Tail0_B_01",
		"Sp_Hi_Tail0_B_02",
		"Sp_Hi_Tail0_B_03",
		"Sp_Hi_Tail0_B_04",
	]
	# 越靠近尾尖，累积旋转越大，用均匀系数即可（骨链会自动累积）
	var world_droop := Vector3(1.0, 0.0, 0.0)  # 世界 X 轴（前后下垂平面）
	for bname in bone_names:
		var bid := _skeleton.find_bone(bname)
		if bid < 0:
			continue
		var gr   := _skeleton.get_bone_global_rest(bid)
		var ax   := (gr.basis.inverse() * world_droop).normalized()
		var base := _skeleton.get_bone_rest(bid).basis.get_rotation_quaternion()
		_skeleton.set_bone_pose_rotation(bid,
			base * Quaternion(ax, deg_to_rad(angle_deg)))


# ── BlendShape 底层操作 ────────────────────────────────────────────────────────

func _set_raw_blend_shape(shape_name: String, value: float, mesh_name: String = "") -> bool:
	for mesh in _mesh_instances:
		var mi := mesh as MeshInstance3D
		if mi.mesh == null:
			continue
		if mesh_name != "" and mi.name != mesh_name:
			continue
		for i in range(mi.mesh.get_blend_shape_count()):
			if mi.mesh.get_blend_shape_name(i) == shape_name:
				mi.set_blend_shape_value(i, value)
				return true
	return false


func _get_blend_shape_value(shape_name: String) -> float:
	for mesh in _mesh_instances:
		var mi := mesh as MeshInstance3D
		if mi.mesh == null:
			continue
		for i in range(mi.mesh.get_blend_shape_count()):
			if mi.mesh.get_blend_shape_name(i) == shape_name:
				return mi.get_blend_shape_value(i)
	return 0.0


# 生成可供 Tween.tween_method 使用的 Callable
func _make_shape_setter(shape_name: String) -> Callable:
	return func(v: float) -> void:
		_set_raw_blend_shape(shape_name, v)


# ── 挥手 Tween ────────────────────────────────────────────────────────────────

func _do_wave() -> void:
	_is_waving = true
	if _wave_tween:
		_wave_tween.kill()

	if _skeleton == null or _skeleton.find_bone("Arm_R") < 0:
		_do_wave_body_fallback()
		return

	var arm_r:   int = _skeleton.find_bone("Arm_R")
	var elbow_r: int = _skeleton.find_bone("Elbow_R")
	var wrist_r: int = _skeleton.find_bone("Wrist_R")

	_wave_tween = create_tween()

	# 1+2. 上臂侧举 + 小臂弯曲同时进行
	_wave_tween.tween_method(
		func(deg: float) -> void:
			var q := (Quaternion(Vector3(1, 0, 0), deg_to_rad(ARM_X))
					* Quaternion(Vector3(0, 1, 0), deg_to_rad(deg)))
			_skeleton.set_bone_pose_rotation(arm_r, q),
		0.0, WAVE_ARM_Y, 0.35
	)
	if elbow_r >= 0:
		_wave_tween.parallel().tween_method(
			func(deg: float) -> void:
				_skeleton.set_bone_pose_rotation(elbow_r,
					Quaternion(Vector3(0, 0, 1), deg_to_rad(deg))),
			0.0, WAVE_ELBOW_Z, 0.35
		)

	# 3. 手腕来回摆动 4 次（Z 轴，先试正负各 30°）
	if wrist_r >= 0:
		for _i in range(4):
			_wave_tween.tween_method(
				func(deg: float) -> void:
					_skeleton.set_bone_pose_rotation(wrist_r,
						Quaternion(Vector3(0, 0, 1), deg_to_rad(deg))),
				0.0, 30.0, 0.18
			)
			_wave_tween.tween_method(
				func(deg: float) -> void:
					_skeleton.set_bone_pose_rotation(wrist_r,
						Quaternion(Vector3(0, 0, 1), deg_to_rad(deg))),
				30.0, -30.0, 0.18
			)
		_wave_tween.tween_method(
			func(deg: float) -> void:
				_skeleton.set_bone_pose_rotation(wrist_r,
					Quaternion(Vector3(0, 0, 1), deg_to_rad(deg))),
			-30.0, 0.0, 0.12
		)
	else:
		_wave_tween.tween_interval(1.5)

	# 4+5. 小臂放回 + 上臂放回同时进行
	if elbow_r >= 0:
		_wave_tween.tween_method(
			func(deg: float) -> void:
				_skeleton.set_bone_pose_rotation(elbow_r,
					Quaternion(Vector3(0, 0, 1), deg_to_rad(deg))),
			WAVE_ELBOW_Z, 0.0, 0.35
		)
		_wave_tween.parallel().tween_method(
			func(deg: float) -> void:
				var q := (Quaternion(Vector3(1, 0, 0), deg_to_rad(ARM_X))
						* Quaternion(Vector3(0, 1, 0), deg_to_rad(deg)))
				_skeleton.set_bone_pose_rotation(arm_r, q),
			WAVE_ARM_Y, 0.0, 0.35
		)
	else:
		_wave_tween.tween_method(
			func(deg: float) -> void:
				var q := (Quaternion(Vector3(1, 0, 0), deg_to_rad(ARM_X))
						* Quaternion(Vector3(0, 1, 0), deg_to_rad(deg)))
				_skeleton.set_bone_pose_rotation(arm_r, q),
			WAVE_ARM_Y, 0.0, 0.35
		)

	_wave_tween.finished.connect(_on_wave_finished, CONNECT_ONE_SHOT)


func _do_wave_body_fallback() -> void:
	# 没有骨骼时退化为轻微全身摇摆
	_wave_tween = create_tween()
	_wave_tween.set_loops(3)
	_wave_tween.tween_property(self, "rotation:z", deg_to_rad(6.0), 0.3)
	_wave_tween.tween_property(self, "rotation:z", deg_to_rad(-6.0), 0.3)
	_wave_tween.finished.connect(_on_wave_finished, CONNECT_ONE_SHOT)


func _on_wave_finished() -> void:
	_is_waving = false
	_state = State.IDLE
