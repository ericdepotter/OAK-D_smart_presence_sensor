import { ApiContext } from '../../App';
import Camera from './Camera';
import React, { useContext, useState, useEffect } from "react";

function Cameras() {
  const api = useContext(ApiContext);
  const [cameras, setCameras] = useState([]);

  useEffect(() => {
    fetch(api.endpoint_api + '/camera_config').then(res => res.json()).then(data => {
        setCameras(data);
    });
  }, []);

  return cameras.map(
    (c, idx) => (
        <Camera camera={c} key={idx}/>
    )
  );
}

export default Cameras;