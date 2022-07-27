import { ApiContext } from "../App";
import React, { useContext, useState, useEffect } from "react";
import socketIOClient from "socket.io-client";

function arrayBufferToBase64(buffer) {
  var binary = '';
  var bytes = new Uint8Array(buffer);
  var len = bytes.byteLength;
  for (var i = 0; i < len; i++) {
    binary += String.fromCharCode(bytes[i]);
  }
  return btoa(binary);

}

function CameraStream() {
  const api = useContext(ApiContext);
  const [image, setImage] = useState("");

  useEffect(() => {
    const socket = socketIOClient(api.endpoint_ws);
    socket.on("camera-stream", data => {
        data = 'data:image/jpeg;base64,' + arrayBufferToBase64(data);
        setImage(data);
    });

    // CLEAN UP THE EFFECT
    return () => socket.disconnect();
  }, []);

  return (
    <img src={image} style={{width: "100%"}}/>
  );
}

export default CameraStream;