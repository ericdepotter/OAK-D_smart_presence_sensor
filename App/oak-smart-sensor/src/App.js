import React from 'react';
import logo from './logo.svg';
import './App.css';
import CameraStream from './Components/CameraStream';
import Map from './Components/Map/Map';

const api = {
  endpoint_api: "http://localhost:5000/api",
  endpoint_ws: "http://localhost:5000/"
};

const ApiContext = React.createContext(null);

function App() {
  return (
    <div className="App">
      <ApiContext.Provider value={api}>
        <div style={{height: "calc(100vh - 96)", width: "100%", padding: 48, display: "flex"}}>
          <div>
            <Map/>
          </div>
          <div style={{height: "100%", width: "30%", padding: 48, display: "flex", flexDirection: "column", alignItems: "center"}}>
            <CameraStream/>
          </div>
        </div>
      </ApiContext.Provider>
    </div>
  );
}

export default App;

export {ApiContext};
