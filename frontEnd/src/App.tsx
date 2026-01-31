import { Navigate, Route, Routes } from "react-router"
import NavigationTabs from './components/navigation'
import './App.css'
import Inventory from "./pages/Inventory"
import Settings from "./pages/Settings"
import Recipe from "./pages/Recipe"
import Bots from "./pages/Bots"


export default function App() {

  return (
    <Routes>
      <Route path="/" element={<NavigationTabs/>}>
        <Route path="inventory" element= {<Inventory/>}/>
        <Route path="recipes" element= {<Recipe/>}/>
        <Route path="settings" element= {<Settings/>}/>
        <Route path="cameraStatus" element= {<Bots/>}/>
        <Route index element={<Navigate to="inventory" replace={true} />} />
        <Route path="*" element={<Navigate to="inventory" replace={true} />} />
      </Route>
    </Routes>
  )
}

