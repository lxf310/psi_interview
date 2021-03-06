import gevent
from gevent import monkey
monkey.patch_all()

from flask import Flask, render_template
from flask_socketio import SocketIO, Namespace
from bsread import source
import argparse
import os
from matplotlib import pyplot
from threading import Lock
from io import BytesIO
import base64

delay = None
async_mode = None
app = Flask(__name__, static_url_path="/static", static_folder="static")
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app, async_mode=async_mode)  
stream_output_port = None
stream_output_host = None
thread = None
thread_lock = Lock()

def processStream():
    """
    Process stream message:
    1. collect stream metadata
    2. generate and encode the corresponding image data
    3. emit the data to connected clients
    """
    with source(host=stream_output_host, port=stream_output_port, receive_timeout=1000) as input_stream:
        while True:
            socketio.sleep(delay)
            message = input_stream.receive()
            if message is None:
                continue
            beam_energy = message.data.data["beam_energy"].value
            repetition_rate = message.data.data["repetition_rate"].value
            image = message.data.data["image"].value
            pyplot.imshow(image)
            figfile = BytesIO()
            pyplot.savefig(figfile, format="jpg")
            figfile.seek(0)
            metadata = {
                'beam_energy': str(beam_energy),
                'repetition_rate': str(repetition_rate),
                'img': str(base64.b64encode(figfile.getvalue()), encoding='utf-8')
            }
            print(beam_energy)
            socketio.emit('server_response', 
                           metadata, 
                           namespace='/test_conn')

@app.route('/')
def index():
    return render_template('index.html')

class MyNamespace(Namespace):
    def on_connect(self):
        """
        Listen to connect event
        """
        global thread
        with thread_lock:
            if thread is None:
                thread = socketio.start_background_task(
                    target=processStream)
                print("create a new thread")
        socketio.emit('server_response', {'beam_energy': '', 'repetition_rate': '', 'img': ''})

    def on_disconnect(self):
        """
        Listen to disconnect event
        """
        print('Client disconned!')

socketio.on_namespace(MyNamespace('/test_conn'))

def main():
    parser = argparse.ArgumentParser(description='Socekt IO server')
    parser.add_argument('-o', '--output_port', default=8888, type=int, help="Stream output port")
    parser.add_argument('-s', '--output_host', default='localhost', type=str, help="Stream output host")
    parser.add_argument('-p', '--server_port', default=5000, type=int, help="Server port")
    parser.add_argument('-d', '--delay', default=1, type=float, help="Delay between each emit action.")
    arguments = parser.parse_args()
    # set the arguments
    global stream_output_port
    global stream_output_host
    stream_output_port = arguments.output_port
    stream_output_host = arguments.output_host
    global delay
    delay = arguments.delay
    socketio.run(app, port=arguments.server_port, debug=True)

if __name__ == "__main__":
    main()
