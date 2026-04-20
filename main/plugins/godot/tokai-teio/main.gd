extends Node3D

var _is_dragging := false
var _window_drag_start := Vector2i.ZERO
var _mouse_drag_start := Vector2i.ZERO

@onready var socket_server: Node = $SocketServer
@onready var character: Node3D = $CharacterRoot


func _ready() -> void:
	get_viewport().transparent_bg = true
	DisplayServer.window_set_flag(
		DisplayServer.WINDOW_FLAG_ALWAYS_ON_TOP, true,
		DisplayServer.MAIN_WINDOW_ID
	)
	socket_server.command_received.connect(_on_command)
	print("TokaiTeio pet started. Socket port: 9999")


func _input(event: InputEvent) -> void:
	# per_pixel_transparency 已让 OS 在透明像素上不发事件给 Godot
	# 所以直接判断鼠标按下即可，只有点到角色（不透明像素）才会触发
	if event is InputEventMouseButton and event.button_index == MOUSE_BUTTON_LEFT:
		if event.pressed:
			_is_dragging = true
			_mouse_drag_start = DisplayServer.mouse_get_position()
			_window_drag_start = DisplayServer.window_get_position(DisplayServer.MAIN_WINDOW_ID)
		else:
			_is_dragging = false
	elif event is InputEventMouseMotion and _is_dragging:
		var delta: Vector2i = DisplayServer.mouse_get_position() - _mouse_drag_start
		DisplayServer.window_set_position(
			_window_drag_start + delta,
			DisplayServer.MAIN_WINDOW_ID
		)


func _on_command(cmd: Dictionary) -> void:
	var command: String = cmd.get("cmd", "")
	var ok := true

	match command:
		# ── 状态切换 ──────────────────────────────────────────────
		"idle":
			character.set_state("idle")
		"talking":
			character.set_state("talking")
		"wave":
			character.set_state("wave")

		# ── 表情预设：{"cmd":"expression","preset":"happy"}
		# preset 可选值：normal/happy/smile/angry/sad/surprised/smug/dere/excited
		# 支持淡入淡出，duration 默认 0.3s
		"expression":
			var preset: String = cmd.get("preset", cmd.get("name", "normal"))
			var duration: float = cmd.get("duration", 0.3)
			ok = character.set_expression(preset, duration)

		# ── 心情动作：{"cmd":"play_action","preset":"happy"}
		"play_action":
			var preset: String = cmd.get("preset", cmd.get("name", "normal"))
			character.play_action(preset)

		# ── 眼睛高光调参：{"cmd":"eye_highlight","param":"hl1_dir_x","value":0.3}
		# param 可选：hl1_dir_x/y  hl1_sharpness  hl1_strength
		#             hl2_dir_x/y  hl2_sharpness  hl2_strength  highlight_alpha
		"eye_highlight":
			var param: String = cmd.get("param", "")
			var value: float   = cmd.get("value", 0.0)
			character.set_eye_highlight_param(param, value)

		# ── 直接操作单个 BlendShape：{"cmd":"blend_shape","name":"Mouth_4_0(WaraiA)[M_Face]","value":0.8}
		"blend_shape":
			var name: String = cmd.get("name", "")
			var value: float = cmd.get("value", 1.0)
			var mesh: String = cmd.get("mesh", "")
			ok = character.set_blend_shape(mesh, name, value)

		# ── 播放动画：{"cmd":"play_animation","name":"RESET"}
		"play_animation":
			var name: String = cmd.get("name", "")
			ok = character.play_animation(name)

		# ── 角色整体绕 Y 轴旋转（前后转身）：{"cmd":"rotate_y","angle":30}
		"rotate_y":
			var angle: float = cmd.get("angle", 0.0)
			character._base_rot_y = deg_to_rad(angle)

		# ── 尾巴下垂调参（调好后填入 action_happy.gd）────────────────
		# {"cmd":"tail_droop","angle":30}  正值向后下垂，负值向前翘
		"tail_droop":
			var angle: float = cmd.get("angle", 0.0)
			character.set_tail_droop(angle)

		# ── 复位姿态 ──────────────────────────────────────────────
		"reset_pose":
			character.reset_pose()

		# ── 窗口控制 ──────────────────────────────────────────────
		"move":
			var x: int = cmd.get("x", 100)
			var y: int = cmd.get("y", 100)
			DisplayServer.window_set_position(Vector2i(x, y), DisplayServer.MAIN_WINDOW_ID)
		"hide":
			get_window().hide()
		"show":
			get_window().show()
		"quit":
			get_tree().quit()
		_:
			ok = false
			push_warning("Unknown command: " + command)

	socket_server.send_response({"status": "ok" if ok else "error", "cmd": command})
