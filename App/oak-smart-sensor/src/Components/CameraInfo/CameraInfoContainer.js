import { CameraContext } from "../../App";
import CameraDetail from "./CameraDetail";
import CameraStream from "./CameraStream";
import React, { useContext } from "react";
import { cloneDeep } from "lodash";

let activeCameraId = null;
let originalCamera = null;

function CameraInfoContainer() {
    const {cameraContext, setCameraContext, activeCameraContext, setActiveCameraContext} = useContext(CameraContext);

    if (activeCameraContext == null) {
        activeCameraId = null;
        originalCamera = null;

        return (
            <div style={{fontSize: 24}}>
                No camera selected
            </div>
        )
    }

    const activeCamera = cloneDeep(cameraContext[activeCameraContext]);

    if (activeCameraContext !== activeCameraId) {
        activeCameraId = activeCameraContext;
        originalCamera = cloneDeep(activeCamera);
    }

    const handleUpdate = (camera) => {
        const updated = cloneDeep(cameraContext);
        updated[activeCameraContext] = camera;
        setCameraContext(updated);
    }

    const handleCancel = () => {
        const updated = cloneDeep(cameraContext);
        updated[activeCameraContext] = originalCamera;
        setCameraContext(updated);
        setActiveCameraContext(null);
    }

    return (
        <React.Fragment>
            <div style={{marginBottom: 8, fontSize: 24}}>Camera: {activeCamera.id}</div>
            <CameraStream/>
            <CameraDetail camera={activeCamera} onUpdate={handleUpdate} onCancel={handleCancel}/>
        </React.Fragment>
    );
}

export default CameraInfoContainer;