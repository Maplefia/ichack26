import { useEffect, useState } from "react"
import { backendServer } from "../CONSTANTS"
import styles from "../styles/Bots.module.css"
import Loading from "../components/loading"

interface BotCardTypes {
    id: string,
    status: "Connected" | "Disconnected"
    battery?: string | undefined
}

function BotCard(botProps: BotCardTypes) {
    const batteryLevel = botProps.battery ? parseInt(botProps.battery) : null;
    const batteryClass = batteryLevel !== null ? (batteryLevel > 20 ? 'high' : 'low') : '';

    return (
        <div className={styles.card}>
            <h2>Sensor {botProps.id}</h2>
            <h3>Status: {botProps.status}</h3>
            {botProps.battery !== undefined && (
                <p className={`${styles.battery} ${styles[batteryClass]}`}>
                    Battery: {botProps.battery}%
                </p>
            )}
        </div>
    )
}

async function fetchBotsFromAPI(): Promise<BotCardTypes[]> {
    try {
        const response = await fetch(`http://${backendServer}/api/bots`)
        if (!response.ok) {
            throw new Error(`API error: ${response.status}`)
        }
        const data = await response.json()
        return data
    } catch (error) {
        console.error('Failed to fetch bots:', error)
        return []
    }
}

export default function Bots() {
    const [botDevices, setBotDevices] = useState<BotCardTypes[] | null>(null);

    useEffect(() => {
        fetchBotsFromAPI().then(data => setBotDevices(data))
    },[])

    return (
        <div>
            <h1 className={styles.pageName}>My devices</h1>
            {botDevices ? (
                <div className={styles.container}>
                    {botDevices.map(bot => (
                        <BotCard key={bot.id} {...bot} />
                    ))}
                </div>
            ) : (
                <div>
                    <Loading message={"Looking for devices..."}/>
                </div>
            )}
        </div>
    )
}