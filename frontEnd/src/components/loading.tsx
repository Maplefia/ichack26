import styles from "../styles/Loading.module.css"

export default function Loading(props: {message: string}) {
    return (
        <div className={styles.container}>
            <h4>{props.message}</h4>
            <div className={styles.loading}>
                <svg className={styles.indicator} viewBox="0 0 100 100">
                    <circle className={styles.circle} cx="50" cy="50" r="45"/>
                </svg>
            </div>
        </div>
    )
}