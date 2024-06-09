from PyQt6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QPushButton, QLabel, QTextEdit, QWidget
from PyQt6.QtCore import QThread, pyqtSignal
import sys
import subprocess
from http.server import HTTPServer, SimpleHTTPRequestHandler
import ngrok
import time
import webbrowser
import requests
import os

def displayNotification(message,title=None,subtitle=None,soundname=None):
	"""
		Display an OSX notification with message title an subtitle
		sounds are located in /System/Library/Sounds or ~/Library/Sounds
	"""
	titlePart = ''
	if(not title is None):
		titlePart = 'with title "{0}"'.format(title)
	subtitlePart = ''
	if(not subtitle is None):
		subtitlePart = 'subtitle "{0}"'.format(subtitle)
	soundnamePart = ''
	if(not soundname is None):
		soundnamePart = 'sound name "{0}"'.format(soundname)

	appleScriptNotification = 'display notification "{0}" {1} {2} {3}'.format(message,titlePart,subtitlePart,soundnamePart)
	os.system("osascript -e '{0}'".format(appleScriptNotification))

def check_internet_connection():
    try:
        subprocess.check_output(["ping", "-c", "1", "8.8.8.8"])
        return True
    except subprocess.CalledProcessError:
        return False

class RequestHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        self.server_ref = kwargs.pop('server_ref', None)
        super().__init__(*args, **kwargs)

    def do_POST(self):
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        # self.server_ref.log(f"Received POST data: {post_data}")
        self.send_response(200)
        self.end_headers()
        if b'"action":"lock"' in post_data:
            subprocess.run(['/usr/bin/pmset', 'displaysleepnow'])
            # webbrowser.open('https://animesuge.to/home')
            self.server_ref.log("Executed lock command")
        elif b'"action":"youtube"' in post_data:
            webbrowser.open('https://www.youtube.com')
            self.server_ref.log("Opened YouTube")
        elif b'"action":"insult"' in post_data:
            response = requests.get('https://insult.mattbas.org/api/insult')
            insult = response.text
            displayNotification(insult, title='Insult')
            self.server_ref.log(f"Received insult: {insult}")

    def log_message(self, format, *args):
        self.server_ref.log("%s - - [%s] %s\n" % (self.address_string(), self.log_date_time_string(), format%args))

class LockScreenServer:
    def __init__(self, port):
        self.port = port
        self.server = None
        self.listener = None

    def start_server(self, log_callback, status_callback):
        handler_class = lambda *args, **kwargs: RequestHandler(*args, server_ref=self, **kwargs)
        self.server = HTTPServer(('', self.port), handler_class)
        self.log = log_callback
        self.log(f"Starting HTTP server on port {self.port}...")
        while not check_internet_connection():
            self.log('Waiting for internet connection...')
            time.sleep(5)
        self.listener = ngrok.connect(authtoken="2cSkk01zeKo1TfxwM7Ii6m3ZiyX_4GGUK9ommudD4LA8gzGCP", addr=f'localhost:{self.port}', domain="puma-glowing-simply.ngrok-free.app", proto="http")
        status_callback(self.listener.url())
        try:
            self.server.serve_forever()
        except KeyboardInterrupt:
            if self.server is not None:
                self.server.server_close()
                self.log('HTTP server stopped.')

    def stop_server(self):
        if self.server is not None:
            self.server.server_close()
            self.log('HTTP server stopped.')
        
        if self.listener is not None:
            ngrok.disconnect(self.listener.url())
            self.log('Ngrok tunnel closed.')

class ServerThread(QThread):
    log_signal = pyqtSignal(str)
    status_signal = pyqtSignal(str)

    def __init__(self, server):
        QThread.__init__(self)
        self.server = server

    def run(self):
        self.server.start_server(self.log, self.update_status)

    def log(self, message):
        self.log_signal.emit(message)

    def update_status(self, status):
        self.status_signal.emit(status)

class MainWindow(QMainWindow):
    def __init__(self):
        super(MainWindow, self).__init__()

        self.server = None
        self.status = "Server not running."
        self.btnstatus = True

        self.setWindowTitle("Lock Screen Server")

        self.port_label = QLabel("Local Port: 7070")
        self.port_label1 = QLabel(f'Ngrok URL: {self.status}')

        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)

        self.start_button = QPushButton("Stop Server")
        self.start_button.clicked.connect(self.check_server)

        layout = QVBoxLayout()
        layout.addWidget(self.port_label)
        layout.addWidget(self.port_label1)
        layout.addWidget(self.log_text)
        layout.addWidget(self.start_button)

        central_widget = QWidget()
        central_widget.setLayout(layout)
        self.setCentralWidget(central_widget)

        self.resize(500, 300)

        self.start_server()

    def log(self, message):
        self.log_text.append(message)

    def update_status(self, status):
        self.status = status
        self.port_label1.setText(f'Ngrok URL:{self.status}')

    def check_server(self):
        if self.btnstatus is True:
            self.start_button.setText("Stop Server")
            self.start_server()
        else :
            self.start_button.setText("Start Server")
            self.stop_server()

    def start_server(self):
        if self.server is None:
            self.server = LockScreenServer(7070)
            self.server_thread = ServerThread(self.server)
            self.server_thread.log_signal.connect(self.log)
            self.server_thread.status_signal.connect(self.update_status)
            self.server_thread.start()
            self.btnstatus = False

    def stop_server(self):
        if self.server is not None:
            self.server.stop_server()
            self.server = None
            self.update_status("Server not running.")
            self.btnstatus = True

def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == '__main__':
    main()