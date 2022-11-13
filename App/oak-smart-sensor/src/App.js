import React, { useEffect, useState } from 'react';
import logo from './logo.svg';
import './App.css';
import CameraInfoContainer from './Components/CameraInfo/CameraInfoContainer';
import Map from './Components/Map/Map';
import '@fontsource/roboto/300.css';
import '@fontsource/roboto/400.css';
import '@fontsource/roboto/500.css';
import '@fontsource/roboto/700.css';

const api = {
  endpoint_api: "http://192.168.2.156:5000/api",
  endpoint_ws: "http://192.168.2.156:5000/"
};

export const ApiContext = React.createContext(null);
export const CameraContext = React.createContext(null);

function App() {
  const [cameraContext, setCameraContext] = useState(null);
  const [activeCameraContext, setActiveCameraContext] = useState(null);

  useEffect(() => {
    fetch(api.endpoint_api + '/camera_config').then(res => res.json()).then(data => {
      const context = {};
      data.forEach(item => context[item.id] = item);
      setCameraContext(context);
    });
  }, []);

  return (
    <div className="App">
      <ApiContext.Provider value={api}>
        <CameraContext.Provider value={{cameraContext, setCameraContext, activeCameraContext, setActiveCameraContext}}>
          <div style={{height: "calc(100vh - 56)", width: "calc(100% - 56)", padding: 28, display: "flex", flexWrap: "wrap"}}>
            <div>
              <Map/>
            </div>
            <div style={{height: "100%", width: "30%", padding: 48, display: "flex", flexDirection: "column", alignItems: "center", flexGrow: 1}}>
              <CameraInfoContainer/>
            </div>
          </div>
        </CameraContext.Provider>
      </ApiContext.Provider>
    </div>
  );
}

export default App;
