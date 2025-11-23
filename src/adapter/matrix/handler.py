import logging
import time
import requests

from datetime import datetime

from generic.api import label_pb2
from generic.api.configuration import ConfigurationItem, Configuration
from generic.api.label import Label, Sort
from generic.api.parameter import Type, Parameter
from generic.handler import Handler as AbstractHandler

def _response(name, channel='matrix', parameters=None):
    return Label(
        sort=Sort.RESPONSE,
        name=name,
        channel=channel,
        parameters=parameters,
        timestamp=None
    )


def _stimulus(name, channel='matrix', parameters=None):
    return Label(
        sort=Sort.STIMULUS,
        name=name,
        channel=channel,
        parameters=parameters,
        timestamp=None
    )

class MatrixHandler(AbstractHandler):
    BASE_URL = "http://localhost:8008"
    begin_wait_time = 5
    in_between_wait_time = 0.5

    def start(self):
        self.test_case_num = 1
        #login
        succes1, login_resp = self._login_user("@alice:localhost", "123")
        if succes1:
            print("Alice has been logged in")
        else:
            print("error while logging Alice in.")
            print(login_resp.json())
            exit()
        self.access_token = login_resp.json()["access_token"]
        self.access_tokens = [self.access_token]
        #get all the rooms to delete
        succes2, room_list_resp = self._get_joined_rooms(self.access_token)
        for room_id in room_list_resp.json()["joined_rooms"]:
            print("deleting", room_id)
            succes3, leave_room_resp = self._leave_room(self.access_token, room_id)
            succes4, forget_room_resp = self._forget_room(self.access_token, room_id)
        #create room
        succes5, room_resp5 = self._create_room(self.access_token, "first room{self.test_case_num}")
        if succes5:
            print("Test room made")
        else:
            print("error while making room")
            print(room_resp5.json())
            exit()
        self.room_ids = [room_resp5.json()["room_id"]]

        self.adapter_core.send_ready()
    
    def stop(self):
        pass
    
    def reset(self):
        self.test_case_num += 1
        #create room
        succes5, room_resp5 = self._create_room(self.access_token, "first room{self.test_case_num}")
        if succes5:
            print("Test room made")
        else:
            print("error while making room")
            print(room_resp5.json())
            exit()
        self.room_ids = [room_resp5.json()["room_id"]]

        self.adapter_core.send_ready()
    
    def stimulate(self, pb_label: label_pb2.Label):
        print("simulate")
        label = Label.decode(pb_label)
        print(label.name, [p.value for p in label.parameters])

        # send confirmation of stimulus back to AMP
        print("sending confirmation")
        pb_label.timestamp = time.time_ns()
        pb_label.physical_label = bytes(label.name, 'UTF-8')
        self.adapter_core.send_stimulus_confirmation(pb_label)

        time.sleep(self.in_between_wait_time)
        print("decoding command")
        command_name = label.name.upper()
        if command_name == "INIT":
            self._handle_stimulus_init()
        elif command_name == "SEND_MESSAGE":
            room_id = label.parameters[0].value
            body = label.parameters[1].value
            txn_id = label.parameters[2].value
            self._handle_stimulus_send_msg(room_id, body, txn_id)
        elif command_name == "REPLY_MESSAGE":
            room_id = label.parameters[0].value
            body = label.parameters[1].value
            parent_event = label.parameters[2].value
            txn_id = label.parameters[3].value
            self._handle_stimulus_reply_msg(room_id, parent_event, body, txn_id)
        elif command_name == "THREAD_MESSAGE":
            room_id = label.parameters[0].value
            body = label.parameters[1].value
            parent_event = label.parameters[2].value
            txn_id = label.parameters[3].value
            self._handle_stimulus_thread_msg(room_id, parent_event, body, txn_id)
        elif command_name == "REDACT_MESSAGE":
            room_id = label.parameters[0].value
            event_id = label.parameters[1].value
            txn_id = label.parameters[2].value
            self._handle_stimulus_redact_msg(room_id, event_id, txn_id)
        else:
            print("unknown label")
    
    def _handle_stimulus_init(self):
        print("_handle_stimulus_init")
        for room_id in self.room_ids:
            sut_msg = _response('created_room', 'matrix', parameters=[Parameter('room_id', Type.STRING, value=room_id)])
            self.adapter_core.send_response(sut_msg)
        print("_handle_stimulus_init2")
        sut_msg2 = Label(
                sort=Sort.RESPONSE,
                name='rooms_ready',
                channel='matrix',
                physical_label=bytes("created room", 'UTF-8'),
                timestamp=None,
                parameters=[])
        self.adapter_core.send_response(sut_msg2)
        print("_handle_stimulus_init done")

    def _handle_stimulus_send_msg(self, room_id, body, txnID):
        print("_handle_stimulus_send_msg")
        succes, resp = self._send_message_in_room(self.access_token, room_id, body, txnID)
        if resp.status_code == 200:
            sut_msg = _response("success", 'matrix', parameters=[Parameter('event_id', Type.STRING, value=resp.json()["event_id"])])
        elif resp.status_code == 400:
            sut_msg = _response("400", 'matrix', parameters=[])
        else:
            sut_msg = _response(str(resp.status_code), 'matrix', parameters=[])
            print(resp.json())
        self.adapter_core.send_response(sut_msg)
        
    def _handle_stimulus_reply_msg(self, room_id, event_id, body, txnID):
        print("_handle_stimulus_reply_msg")
        succes, resp = self._reply_message_in_room(self.access_token, room_id, event_id, body, txnID)
        if resp.status_code == 200:#access_token, room_id, msg, event_id, tnxID
            sut_msg = _response("success", 'matrix', parameters=[Parameter('event_id', Type.STRING, value=resp.json()["event_id"])])
        elif resp.status_code == 400:
            sut_msg = _response("400", 'matrix', parameters=[])
        else:
            sut_msg = _response(str(resp.status_code), 'matrix', parameters=[])
            print(resp.json())
        self.adapter_core.send_response(sut_msg)

    def _handle_stimulus_thread_msg(self, room_id, event_id, body, txnID):
        print("_handle_stimulus_thread_msg")
        succes, resp = self._thread_message_in_room(self.access_token, room_id, event_id, body, txnID)
        print(resp.json())
        if resp.status_code == 200:#access_token, room_id, msg, event_id, tnxID
            sut_msg = _response("success", 'matrix', parameters=[Parameter('event_id', Type.STRING, value=resp.json()["event_id"])])
        elif resp.status_code == 400:
            sut_msg = _response("400", 'matrix', parameters=[])
            print(resp.json())
        else:
            sut_msg = _response(str(resp.status_code), 'matrix', parameters=[])
            print(resp.json())
        self.adapter_core.send_response(sut_msg)

    def _handle_stimulus_redact_msg(self, room_id, event_id, txnID):
        print('_handle_stimulus_redact_msg')
        succes, resp = self._redact_message_in_room(self.access_token, room_id, event_id, txnID)
        if resp.status_code == 200:
            sut_msg = _response("success", 'matrix', parameters=[Parameter('event_id', Type.STRING, value=resp.json()["event_id"])])
        elif resp.status_code == 400:
            sut_msg = _response("400", 'matrix', parameters=[])
        else:
            sut_msg = _response(str(resp.status_code), 'matrix', parameters=[])
            print(resp.json())
        self.adapter_core.send_response(sut_msg)

    def supported_labels(self):
        """
        The labels supported by the adapter.

        Returns:
             [Label]: List of all supported labels of this adapter
        """
        return [
            _stimulus('init', parameters=[]),

            _stimulus('send_message', parameters=[Parameter('room_id', Type.STRING,), 
                                              Parameter('body', Type.STRING,), 
                                              Parameter('txn_id', Type.INTEGER)]),

            _stimulus('reply_message', parameters=[Parameter('room_id', Type.STRING,), 
                                               Parameter('body', Type.STRING,), 
                                               Parameter('parent_event', Type.STRING,), 
                                               Parameter('txn_id', Type.INTEGER)]),

            _stimulus('thread_message', parameters=[Parameter('room_id', Type.STRING,), 
                                               Parameter('body', Type.STRING,), 
                                               Parameter('parent_event', Type.STRING,), 
                                               Parameter('txn_id', Type.INTEGER)]),

            _stimulus('redact_message', parameters=[Parameter('room_id', Type.STRING,), 
                                               Parameter('event_id', Type.STRING,), 
                                               Parameter('txn_id', Type.INTEGER)]),

            _response('created_room', parameters=[Parameter('room_id', Type.STRING)]),

            _response('rooms_ready', parameters=[]),

            _response('success', parameters=[Parameter('event_id', Type.STRING,)]),
            
            _response('400', parameters=[]),

            _response('403', parameters=[]),
        ]
    
    def get_configuration(self) -> Configuration:
        """
        The default configuration of this adapter.

        Returns:
            Configuration: the default configuration required by this adapter.
        """
        return Configuration([])
    
    def default_configuration(self) -> Configuration:
        """
        The default configuration of this adapter.

        Returns:
            Configuration: the default configuration required by this adapter.
        """
        return Configuration([])

    def _login_user(self, username, password):
        login_resp = requests.post(
                f"{self.BASE_URL}/_matrix/client/v3/login",
                json={
                    "type": "m.login.password",
                    "identifier": {
                        "type": "m.id.user",
                        "user": username
                    },
                    "password": password
                }
            )
        while login_resp.status_code==429:
            #trying again until success
            print(login_resp.json())
            print(f"login request timed out. trying again after wait of {login_resp.json()['retry_after_ms']*0.001+1}")
            time.sleep(login_resp.json()['retry_after_ms']*0.001+1)
            login_resp = requests.post(
                f"{self.BASE_URL}/_matrix/client/v3/login",
                json={
                    "type": "m.login.password",
                    "identifier": {
                        "type": "m.id.user",
                        "user": username
                    },
                    "password": password
                }
            )

        succes = login_resp.status_code == 200
        return succes, login_resp
    
    def _create_room(self, access_token, name):
        headers = {"Authorization": f"Bearer {access_token}"}
        room_resp = requests.post(
                f"{self.BASE_URL}/_matrix/client/r0/createRoom",
                headers=headers,
                json={
                    "name": name,
                    "preset": "public_chat",
                    #"room_alias_name": alias,
                    "topic": "All about happy hour"
                }
            )
        while room_resp.status_code==429:
            print(f"create room request timed out. trying again after wait of {room_resp.json()['retry_after_ms']*0.001+1}")
            time.sleep(room_resp.json()['retry_after_ms']*0.001+1)
            room_resp = requests.post(
                f"{self.BASE_URL}/_matrix/client/r0/createRoom",
                headers=headers,
                json={
                    "name": name,
                    "preset": "public_chat",
                    #"room_alias_name": alias,
                    "topic": "All about happy hour"
                }
            )

        succes = room_resp.status_code == 200
        return succes, room_resp
    
    def _leave_room(self, access_token, room_id):
        headers = {"Authorization": f"Bearer {access_token}"}
        leave_resp = requests.post(
            f"{self.BASE_URL}/_matrix/client/v3/rooms/{room_id}/leave",
            headers=headers,
            json={
                "reason": "Saying farewell - thanks for the support!"
            }
        )
        while leave_resp.status_code==429:
            print(f"create room request timed out. trying again after wait of {leave_resp.json()['retry_after_ms']*0.001+1}")
            time.sleep(leave_resp.json()['retry_after_ms']*0.001+1)
            leave_resp = requests.post(
                f"{self.BASE_URL}/_matrix/client/v3/rooms/{room_id}/leave",
                headers=headers,
                json={
                    "reason": "Saying farewell - thanks for the support!"
                }
            )

        return leave_resp.status_code == 200, leave_resp
    
    def _forget_room(self, access_token, room_id):
        # probably good practice, but does not seem to actually forget room.
        # According to specification:
        '''
        This API stops a user remembering about a particular room.
        In general, history is a first class citizen in Matrix. After this API is called, however, a user will no longer be able to retrieve history for this room. If all users on a homeserver forget a room, the room is eligible for deletion from that homeserver.
        If the user is currently joined to the room, they must leave the room before calling this API.
        '''
        headers = {"Authorization": f"Bearer {access_token}"}
        forget_resp = requests.post(
            f"{self.BASE_URL}/_matrix/client/v3/rooms/{room_id}/forget",
            headers=headers,
            json={}
        )
        while forget_resp.status_code==429:
            print(f"create room request timed out. trying again after wait of {forget_resp.json()['retry_after_ms']*0.001+1}")
            time.sleep(forget_resp.json()['retry_after_ms']*0.001+1)
            forget_resp = requests.post(
                f"{self.BASE_URL}/_matrix/client/v3/rooms/{room_id}/forget",
                headers=headers,
                json={}
            )

        return forget_resp.status_code == 200, forget_resp
    
    def _get_joined_rooms(self, access_token):
        headers = {"Authorization": f"Bearer {access_token}"}
        room_resp = requests.get(
            f"{self.BASE_URL}/_matrix/client/v3/joined_rooms",
            headers=headers,
            json={}
        )
        while room_resp.status_code==429:
            print(f"create room request timed out. trying again after wait of {room_resp.json()['retry_after_ms']*0.001+1}")
            time.sleep(room_resp.json()['retry_after_ms']*0.001+1)
            room_resp = requests.get(
                f"{self.BASE_URL}/_matrix/client/v3/joined_rooms",
                headers=headers,
                json={}
            )

        succes = room_resp.status_code == 200
        return succes, room_resp

    def _send_message_in_room(self, access_token, room_id, msg, tnxID, eventType = "m.room.message", msgType = "m.text"):
        # 3 Send a message
        headers = {"Authorization": f"Bearer {access_token}"}
        message_resp = requests.put(
            f"{self.BASE_URL}/_matrix/client/r0/rooms/{room_id}/send/{eventType}/{tnxID}",
            headers=headers,
            json={
                "msgtype": msgType,
                "body": msg
            }
        )
        while message_resp.status_code==429:
            print(f"send message request timed out. trying again after wait of {message_resp.json()['retry_after_ms']*0.001+1}")
            time.sleep(message_resp.json()['retry_after_ms']*0.001+1)
            message_resp = requests.put(
                f"{self.BASE_URL}/_matrix/client/r0/rooms/{room_id}/send/{eventType}/{tnxID}",
                headers=headers,
                json={
                    "msgtype": msgType,
                    "body": msg
                }
            )

        return message_resp.status_code == 200, message_resp
    
    def _reply_message_in_room(self, access_token, room_id, msg, event_id, tnxID, eventType = "m.room.message", msgType = "m.text"):
        # 3 Reply to a message
        headers = {"Authorization": f"Bearer {access_token}"}
        reply_resp = requests.put(
            f"{self.BASE_URL}/_matrix/client/r0/rooms/{room_id}/send/{eventType}/{tnxID}",
            headers=headers,
            json={
                "msgtype": msgType,
                "body": msg,
                "m.relates_to": {
                    "m.in_reply_to": {
                        "event_id": event_id
                    }
                }
            }
        )
        while reply_resp.status_code==429:
            print(f"reply message request timed out. trying again after wait of {reply_resp.json()['retry_after_ms']*0.001+1}")
            time.sleep(reply_resp.json()['retry_after_ms']*0.001+1)
            reply_resp = requests.put(
                f"{self.BASE_URL}/_matrix/client/r0/rooms/{room_id}/send/{eventType}/{tnxID}",
                headers=headers,
                json={
                    "msgtype": msgType,
                    "body": msg,
                    "m.relates_to": {
                        "m.in_reply_to": {
                            "event_id": event_id
                        }
                    }
                }
            )
        print(reply_resp.json())
        return reply_resp.status_code == 200, reply_resp
    
    def _thread_message_in_room(self, access_token, room_id, msg, event_id, tnxID, eventType = "m.room.message", msgType = "m.text"):
        # 3 Send a message
        headers = {"Authorization": f"Bearer {access_token}"}
        thread_resp = requests.put(
            f"{self.BASE_URL}/_matrix/client/r0/rooms/{room_id}/send/{eventType}/{tnxID}",
            headers=headers,
            json={
                "msgtype": msgType,
                "body": msg,
                "m.relates_to": {
                    "rel_type": "m.thread",
                    "event_id": event_id
                }
            }
        )
        while thread_resp.status_code==429:
            print(f"reply message request timed out. trying again after wait of {thread_resp.json()['retry_after_ms']*0.001+1}")
            time.sleep(thread_resp.json()['retry_after_ms']*0.001+1)
            thread_resp = requests.put(
                f"{self.BASE_URL}/_matrix/client/r0/rooms/{room_id}/send/{eventType}/{tnxID}",
                headers=headers,
                json={
                    "msgtype": msgType,
                    "body": msg,
                    "m.relates_to": {
                        "rel_type": "m.thread",
                        "event_id": event_id
                    }
                }
            )
        return thread_resp.status_code == 200, thread_resp
    
    def _redact_message_in_room(self, access_token, room_id, event_id, txnID):
        #PUT /_matrix/client/v3/rooms/{roomId}/redact/{eventId}/{txnId}
        print('_redact_message_in_room')
        headers = {"Authorization": f"Bearer {access_token}"}
        message_resp = requests.put(
            f"{self.BASE_URL}/_matrix/client/v3/rooms/{room_id}/redact/{event_id}/{txnID}",
            headers=headers,
            json={}
        )
        while message_resp.status_code==429:
            print(f"send message request timed out. trying again after wait of {message_resp.json()['retry_after_ms']*0.001+1}")
            time.sleep(message_resp.json()['retry_after_ms']*0.001+1)
            message_resp = requests.put(
                f"{self.BASE_URL}/_matrix/client/v3/rooms/{room_id}/redact/{event_id}/{txnID}",
                headers=headers,
                json={}
            )

        return message_resp.status_code == 200, message_resp
    
