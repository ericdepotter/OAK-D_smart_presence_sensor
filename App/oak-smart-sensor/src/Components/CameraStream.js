import { ApiContext } from "../App";
import React, { useContext, useState, useEffect } from "react";
import socketIOClient from "socket.io-client";

function CameraStream() {
  const api = useContext(ApiContext);
  const [image, setImage] = useState("");

  useEffect(() => {
    const socket = socketIOClient(api.endpoint_ws);
    socket.on("camera-stream", data => {
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