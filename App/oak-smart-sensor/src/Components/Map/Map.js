import { ApiContext } from "../../App";
import Cameras from "./Cameras";
import {CRS} from 'leaflet';
import { ImageOverlay, MapContainer } from "react-leaflet";
import PersonsDetected from "./PersonsDetected";
import React, { useContext, useState, useEffect } from "react";
import Zones from "./Zones";

function Map(props) {
  const api = useContext(ApiContext);
  const [dimensions, setDimensions] = useState([]);

  useEffect(() => {
    fetch(api.endpoint_api + '/map_dimensions').then(res => res.json()).then(data => {
        setDimensions([data.width, data.height]);
    });
  }, []);

  return dimensions.length > 0 && (
    <MapContainer zoom={-8}
                  center={[dimensions[0]/2, dimensions[1]/2]}
                  style={{'width': dimensions[0], 'height': dimensions[1], 'transform': 'None'}}
                  crs={CRS.Simple}
                  dragging={false}
                  zoomControl={false}
                  scrollWheelZoom={false}
                  doubleClickZoom={false}
                  boxZoom={false}>
      <ImageOverlay url={'img/House plan.png'}
                    bounds={[[0,0], [dimensions[1], dimensions[0]]]}
                    className="no-transform"/>
      <Zones/>
      <Cameras/>
      <PersonsDetected/>
    </MapContainer>
  );
}

export default Map;