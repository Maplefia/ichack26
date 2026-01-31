import { NavLink, Outlet } from "react-router"
import { FaBoxOpen, FaCog, FaCamera } from "react-icons/fa";
import { FaBowlFood } from "react-icons/fa6";
import styles from "../styles/Navigator.module.css"

export default function NavigationTabs() {
    return (
        <>
            <div className={styles.main}>
                <NavLink to="/inventory" className={({ isActive }: { isActive: boolean }) => `tab${isActive ? " active" : ""}`}>
                    <FaBoxOpen/>
                </NavLink>
                <NavLink to="/recipes" className={({ isActive }: { isActive: boolean }) => `tab${isActive ? " active" : ""}`}>
                    <FaBowlFood/>
                </NavLink>
                <NavLink to="/settings" className={({ isActive }: { isActive: boolean }) => `tab${isActive ? " active" : ""}`}>
                    <FaCog/>
                </NavLink>
                <NavLink to="/cameraStatus" className={({ isActive }: { isActive: boolean }) => `tab${isActive ? " active" : ""}`}>
                    <FaCamera/>
                </NavLink>
            </div>
            <Outlet />
        </>
    )
}