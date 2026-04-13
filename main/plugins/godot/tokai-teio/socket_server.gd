extends Node

## TCP Socket 服务器，监听来自 Python 主程序的命令
## 协议：每条命令为一行 JSON，以 \n 结尾
## 示例命令：
##   {"cmd": "idle"}
##   {"cmd": "talking"}
##   {"cmd": "wave"}
##   {"cmd": "move", "x": 200, "y": 100}
##   {"cmd": "hide"}
##   {"cmd": "show"}
##   {"cmd": "quit"}

signal command_received(cmd: Dictionary)

const PORT := 9999

var _server := TCPServer.new()
var _client: StreamPeerTCP = null
var _buffer := ""


func _ready() -> void:
	var err := _server.listen(PORT)
	if err != OK:
		push_error("SocketServer: 无法监听端口 %d — %s" % [PORT, error_string(err)])
	else:
		print("SocketServer: 监听端口 %d" % PORT)


func _process(_delta: float) -> void:
	# 接受新连接（同时只保留一个客户端）
	if _server.is_connection_available():
		if _client and _client.get_status() == StreamPeerTCP.STATUS_CONNECTED:
			_client.disconnect_from_host()
		_client = _server.take_connection()
		_buffer = ""
		print("SocketServer: 客户端已连接")

	if _client == null:
		return

	var status := _client.get_status()
	if status == StreamPeerTCP.STATUS_CONNECTED:
		var available := _client.get_available_bytes()
		if available > 0:
			var data := _client.get_utf8_string(available)
			if data.length() > 0:
				_buffer += data
				_flush_buffer()
	elif status == StreamPeerTCP.STATUS_NONE or status == StreamPeerTCP.STATUS_ERROR:
		print("SocketServer: 客户端已断开")
		_client = null


func _flush_buffer() -> void:
	var pos := _buffer.find("\n")
	while pos != -1:
		var line := _buffer.substr(0, pos).strip_edges()
		_buffer = _buffer.substr(pos + 1)
		if line.length() > 0:
			_parse_line(line)
		pos = _buffer.find("\n")


func _parse_line(line: String) -> void:
	var json := JSON.new()
	var err := json.parse(line)
	if err == OK and json.data is Dictionary:
		command_received.emit(json.data)
	else:
		push_warning("SocketServer: 无效命令 — " + line)


func send_response(data: Dictionary) -> void:
	if _client and _client.get_status() == StreamPeerTCP.STATUS_CONNECTED:
		var msg := JSON.stringify(data) + "\n"
		_client.put_data(msg.to_utf8_buffer())
