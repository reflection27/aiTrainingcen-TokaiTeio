# test_expressions.gd
# 挂到 Main 场景中任意节点即可启用。
# 操作：
#   ← / →  切换表情+动作
#   Space   重播当前动作
#   T       切换 talking/idle 状态（测试口型）
#
# 使用方法：在 main.tscn 里 Add Child Node → Node，
# 将此脚本拖入 Script 栏，运行即可。

extends Node

const PRESETS: Array[String] = [
	"normal", "happy", "smile", "angry",
	"sad", "surprised", "smug", "dere", "excited"
]

var _idx: int = 0
var _talking: bool = false

@onready var _character: Node3D = get_parent().get_node("CharacterRoot")
@onready var _label: Label = _make_label()


func _ready() -> void:
	add_child(_label)
	_apply_current()
	print("[TestExpr] 启动。← → 切换表情，Space 重播动作，T 切 talking/idle")


func _input(event: InputEvent) -> void:
	if not event is InputEventKey or not event.pressed:
		return
	match event.keycode:
		KEY_RIGHT:
			_idx = (_idx + 1) % PRESETS.size()
			_apply_current()
		KEY_LEFT:
			_idx = (_idx - 1 + PRESETS.size()) % PRESETS.size()
			_apply_current()
		KEY_SPACE:
			_character.play_action(PRESETS[_idx])
			print("[TestExpr] 重播动作：%s" % PRESETS[_idx])
		KEY_T:
			_talking = not _talking
			_character.set_state("talking" if _talking else "idle")
			print("[TestExpr] 状态：%s" % ("talking" if _talking else "idle"))


func _apply_current() -> void:
	var name: String = PRESETS[_idx]
	_character.set_expression(name)
	_character.play_action(name)
	_label.text = "[%d/%d] %s" % [_idx + 1, PRESETS.size(), name]
	print("[TestExpr] 切换 → %s" % name)


func _make_label() -> Label:
	var canvas := CanvasLayer.new()
	var lbl := Label.new()
	lbl.position = Vector2(10, 10)
	lbl.add_theme_font_size_override("font_size", 20)
	lbl.add_theme_color_override("font_color", Color.WHITE)
	lbl.add_theme_color_override("font_shadow_color", Color.BLACK)
	lbl.add_theme_constant_override("shadow_offset_x", 2)
	lbl.add_theme_constant_override("shadow_offset_y", 2)
	canvas.add_child(lbl)
	add_child(canvas)
	return lbl
