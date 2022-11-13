import { ApiContext } from "../../App";
import React, { useContext } from "react";
import Input from "../Input";

function CameraDetail(props) {
    const api = useContext(ApiContext);
    const {camera, onCancel, onUpdate} = props;

    const save = () => {
        fetch(api.endpoint_api + '/camera/' + camera.id, {
            method: 'POST',
            headers: {
                'Accept': 'application/json',
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(camera)
        });
    };

    return (
        <div style={{width: "100%"}}>
            <div>
                <h4>Position</h4>
                <div>
                    <Input item={camera} path={"position[0]"} label="X" type="number" onUpdate={onUpdate} style={{marginRight: 16}}/>
                    <Input item={camera} path={"position[1]"} label="Y" type="number" onUpdate={onUpdate}/>
                </div>
            </div>
            <div>
                <h4>Rotation</h4>
                <div>yaw: {camera.rotation[0]}, pitch: {camera.rotation[1]}, roll: {camera.rotation[2]}</div>
            </div>
            <div style={{marginTop: "1.33em"}}>
                <input type="button" onClick={save} value={"Save"}/>
                <input type="button" onClick={onCancel} value={"Cancel"}/>
            </div>
        </div>
    );
}

export default CameraDetail;