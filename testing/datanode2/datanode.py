import logging
import os, requests
import shutil

from flask import Flask, Response, jsonify, request, send_file

HOST = '0.0.0.0'
PORT = 8086
CURRENT_DIR = os.path.join(os.getcwd(), "data")
app = Flask(__name__)
logging.basicConfig(filename='datanode.log', level=logging.DEBUG)


@app.route("/ping")
def ping():
    return Response("ping from datanode", 200)


@app.route("/format")
def format():
    '''
    Formats the contents of the datanode
    '''
    global CURRENT_DIR
    print("started FORMATTING in DATANODE")

    # create root folder if it does not exist
    if not os.path.exists(CURRENT_DIR):
        os.mkdir(CURRENT_DIR)

    # iterate through all files and dirs and delete
    for filename in os.listdir(CURRENT_DIR):
        path = os.path.join(CURRENT_DIR, filename)
        try:
            if os.path.isfile(path) or os.path.islink(path):
                os.unlink(path)
            elif os.path.isdir(path):
                shutil.rmtree(path)
        except Exception as e:
            # if file/dir was not deleted write to log
            print(f"FAILED to DELETE {path} because of\n{e}")
            app.logger.info(f'failed to delete {path}, reason: {e}')

    # obtain info about free space
    _, _, free = shutil.disk_usage(CURRENT_DIR)

    return jsonify({"free": free})


@app.route("/get", methods=['GET'])
def get_file():
    '''
    Get file from datanode
    '''

    print("started transmitting file for get_file")
    file_id = request.json['file_id']

    if os.path.isfile(os.path.join(CURRENT_DIR, str(file_id))):
        print("file found, sending")
        return send_file(os.path.join(CURRENT_DIR, str(file_id)))
    else:
        print("file is not found")
        return Response("file doesn't exist in this node", 404)


@app.route("/copy/existing", methods=['POST'])
def copy_existing_file():
    '''
    Makes copy of the existing file in datanode
    '''
    print("started copying existing file")
    original_id = str(request.json['original_id'])
    copy_id = str(request.json['copy_id'])
    print(f"original id: {original_id}")
    print(f"copy id: {copy_id}")

    path_original = os.path.join(CURRENT_DIR, original_id)
    path_copy = os.path.join(CURRENT_DIR, copy_id)

    try:
        shutil.copyfile(path_original, path_copy)
        print("file was copied")
        return Response("file was copied", 200)
    except Exception as e:
        print(f"file wasn't copied because of {e}")
        return Response(f"file wasn't copied because of {e}", 419)


@app.route('/get-replica', methods=['POST'])
def get_replica():
    '''
    Getting replica of the file from the other datanode
    '''
    print("started acquiring the replica")
    file_id = str(request.json['file_id'])
    src = str(request.json['datanode'])
    print(f"file id: {file_id}")
    print(f"src: {src}")

    path = os.path.join(CURRENT_DIR, file_id)

    try:
        response = requests.get(src + '/get', json={'file_id': file_id})
    except Exception as e:
        print(f"FAILED to get file from {src} due to {e}")
        return Response("error in get", 400)

    if response.status_code // 100 == 2:
        print(f"file was acquired")
        open(path, 'wb').write(response.content)
        return Response("file was replicated", 200)
    else:
        print(f"couldn't acquire the file from {src}")
        return Response("file was not replicated", 400)


@app.route("/copy/non-existing", methods=['POST'])
def copy_non_existing_file():
    '''
    Copying files by obtaining it from the other datanode
    '''
    print("started copying non-existing file")
    original_id = str(request.json['original_id'])
    copy_id = str(request.json['copy_id'])
    src = str(request.json['datanode'])
    print(f"original id: {original_id}")
    print(f"copy id: {copy_id}")
    print(f"src: {src}")

    path_copy = os.path.join(CURRENT_DIR, copy_id)

    try:
        response = requests.get(src + '/get', json={'file_id': original_id})
    except Exception as e:
        print(f"FAILED to get file from {src} due to\n{e}")
        return Response(f"FAILED to get file from {src} due to\n{e}")

    if response.status_code // 100 == 2:
        print(f"file was acquired")
        open(path_copy, 'wb').write(response.content)
        return Response("file was copied", 200)
    else:
        print(f"couldn't acquire the file from {src}")
        return Response("file was not copied", 400)


@app.route("/delete", methods=['DELETE'])
def delete_file():
    print("started deleting file")
    file_id = str(request.json['file_id'])
    print(f"id: {file_id}")

    if os.path.isfile(os.path.join(CURRENT_DIR, file_id)):
        print("file is found")
        os.unlink(os.path.join(CURRENT_DIR, file_id))
        print("file is deleted")
        return Response("file was deleted", 200)
    else:
        print("file is not found")
        return Response("file doesn't exist", 404)


@app.route("/put", methods=['POST'])
def put_file():
    '''
    Put file to datanode
    '''

    print("started putting file")
    # obtain file from client
    file_id = [k for k in request.files.keys()][0]
    file = request.files[f'{file_id}']
    try:
        # create file
        print(f"file: {file}")
        print(f"file id: {file_id}")
        file.save(os.path.join(CURRENT_DIR, str(file_id)))
        return Response("ok", 200)
    except Exception as e:
        # if not created append to log, response 400
        app.logger.info(f"FAILED to put file because of {e}")
        return Response(f"FAILED to put file because of {e}", 400)


@app.route("/create", methods=["POST"])
def create_file():
    '''
    Creates an empty file in the current directory
    '''
    # obtain file id from client
    print("started creating file")
    file_id = request.json['file_id']
    try:
        # create file
        open(CURRENT_DIR + '/' + str(file_id), 'a').close()
        return Response("", 200)
    except Exception as e:
        # if not created append to log, response 400
        app.logger.info(f"failed to create file because of\n{e}")
        return Response(f"failed to create file because of {e}", 400)


if __name__ == '__main__':
    app.run(debug=True, host=HOST, port=PORT)
