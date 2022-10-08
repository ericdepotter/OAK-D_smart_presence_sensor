import { ApiContext } from '../../App';
import PolygonWithText from './PolygonWithText';
import React, { useContext, useState, useEffect } from "react";
import socketIOClient from "socket.io-client";

function Zones(props) {
  const api = useContext(ApiContext);
  const [zones, setZones] = useState({});
  const [zonesOcuppancy, setZonesOcuppancy] = useState({});
  
  useEffect(() => {
    fetch(api.endpoint_api + '/zones').then(res => res.json()).then(data => {
        setZones(data);
    });
  }, []);

  useEffect(() => {
    const socket = socketIOClient(api.endpoint_ws);
    socket.on("zone-stream", data => {
        setZonesOcuppancy(data);
    });

    // CLEAN UP THE EFFECT
    return () => socket.disconnect();
  }, []);

  //console.log(new Date(), zonesOcuppancy, zonesOcuppancy["living"] > 0);

  return Object.keys(zones).map(
    (name, idx) => (
        <PolygonWithText
            className={zonesOcuppancy[name] > 0 ? "active-zone" : ""}
            coords={zones[name]} 
            key={name}
            opacity={zonesOcuppancy[name] > 0 ? 1 : .5}
            fillOpacity={zonesOcuppancy[name] > 0 ? 0.2 : 0.1}
            style={{
              'fill-opacity': zonesOcuppancy[name] > 0 ? 0.2 : 0.1,
              'opacity': zonesOcuppancy[name] > 0 ? 1 : .5
            }}
            text={`${name}: ${zonesOcuppancy[name] || 0}`}/>
    )
  );
}

export default Zones;