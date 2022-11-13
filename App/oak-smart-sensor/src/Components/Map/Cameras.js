import { CameraContext } from '../../App';
import Camera from './Camera';
import React, { useContext } from "react";
import { cloneDeep } from 'lodash';

function Cameras() {
  const {cameraContext, setCameraContext} = useContext(CameraContext);

  const handlePositionUpdate = (cameraId, position) => {
    const updated = cloneDeep(cameraContext);
    updated[cameraId].position = position;
    setCameraContext(updated);
  };

  return cameraContext && Object.values(cameraContext).map(
    (c, idx) => (
        <Camera camera={c} onPositionUpdate={handlePositionUpdate} key={idx}/>
    )
  );
}

export default Cameras;