import React from 'react';
import L from 'leaflet';
import { Marker, Polygon } from 'react-leaflet';

const PolygonWithText = props => {
  const {coords, text, ...propsExtra} = props;

  if (!coords || coords.length == 0) {
    return null;
  }

  var nw = L.polygon(coords).getBounds().getNorthWest();
  var textPoint = [nw.lat - 15, nw.lng + 20];

  const textDiv = L.divIcon({html: text});

  return(
    <Polygon color='blue' positions={coords} {...propsExtra}>
      <Marker position={textPoint} icon={textDiv}/>
    </Polygon>
  );
}

export default PolygonWithText