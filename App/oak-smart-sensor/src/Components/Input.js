import React, { useEffect, useState } from "react";
import MUITextfield from '@mui/material/TextField';
import {get, set} from "lodash";

function Input(props) {
    const {item, onUpdate, path, type, ...otherProps} = props;
    const isNumber = type === "number";

    const [value, setValue] = useState(get(item, path));

    const submitValue = (event) => {
        set(item, path, isNumber ? Number(event.target.value) : event.target.value);
        onUpdate(item);
    }

    useEffect(() => setValue(get(item, path)), [item]);

    return (
        <MUITextfield
            onBlur={submitValue}
            onChange={item => setValue(item.target.value)}
            type={type}
            value={value}
            variant="standard"
            {...otherProps}/>
    );
}

export default Input;