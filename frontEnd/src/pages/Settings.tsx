import { useState} from "react";
import styles from "../styles/Settings.module.css";

const ALLERGEN_OPTIONS = ["peanuts", "tree nuts", "dairy", "eggs", "soy", "wheat", "fish", "shellfish"];
const DEFAULT_EXPIRY_WARNING_DAYS = 3;

export default function Settings() {
    const [allergens, setAllergens] = useState<string[]>(() => {
        const saved = localStorage.getItem('allergens');
        return saved ? JSON.parse(saved) : [];
    });

    const [customAllergens, setCustomAllergens] = useState<string[]>(() => {
        const saved = localStorage.getItem('customAllergens');
        return saved ? JSON.parse(saved) : [];
    });

    const [newAllergen, setNewAllergen] = useState('');
    const [dropdownOpen, setDropdownOpen] = useState(false);

    const [expiryWarningDays, setExpiryWarningDays] = useState<number>(() => {
        const saved = localStorage.getItem('expiryWarningDays');
        return saved ? parseInt(saved) : DEFAULT_EXPIRY_WARNING_DAYS;
    });

    const allAllergens = [...ALLERGEN_OPTIONS, ...customAllergens];

    const handleAllergenChange = (allergen: string) => {
        setAllergens(prev => {
            const updated = prev.includes(allergen)
                ? prev.filter(a => a !== allergen)
                : [...prev, allergen];
            localStorage.setItem('allergens', JSON.stringify(updated));
            return updated;
        });
    };

    const handleAddCustomAllergen = () => {
        if (newAllergen.trim() && !allAllergens.includes(newAllergen.trim())) {
            const updated = [...customAllergens, newAllergen.trim()];
            setCustomAllergens(updated);
            localStorage.setItem('customAllergens', JSON.stringify(updated));
            setNewAllergen('');
        }
    };

    const handleRemoveCustomAllergen = (allergen: string) => {
        const updated = customAllergens.filter(a => a !== allergen);
        setCustomAllergens(updated);
        localStorage.setItem('customAllergens', JSON.stringify(updated));
        
        // Also remove from selected allergens if present
        if (allergens.includes(allergen)) {
            handleAllergenChange(allergen);
        }
    };

    const handleExpiryWarningChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        const value = Math.max(1, parseInt(e.target.value) || DEFAULT_EXPIRY_WARNING_DAYS);
        console.log("Changed expiry warning to ", value)
        setExpiryWarningDays(value);
        localStorage.setItem('expiryWarningDays', value.toString());
        
        // Dispatch custom event to notify other components
        window.dispatchEvent(new Event('settingsChanged'));
    };

    return (
        <div className={styles.container}>
            <h1 className={styles.pageName}>Settings</h1>

            {/* Allergens Section */}
            <div className={styles.section}>
                <h2>Allergens</h2>
                <div className={styles.dropdownContainer}>
                    <button
                        className={styles.dropdownButton}
                        onClick={() => setDropdownOpen(!dropdownOpen)}
                    >
                        {allergens.length > 0
                            ? `${allergens.length} selected`
                            : 'Select allergens'}
                        <span>{dropdownOpen ? '▼' : '▶'}</span>
                    </button>

                    {dropdownOpen && (
                        <div className={styles.dropdownMenu}>
                            {allAllergens.map(allergen => (
                                <div key={allergen} className={styles.dropdownItem}>
                                    <input
                                        type="checkbox"
                                        id={`allergen-${allergen}`}
                                        checked={allergens.includes(allergen)}
                                        onChange={() => handleAllergenChange(allergen)}
                                    />
                                    <label htmlFor={`allergen-${allergen}`}>
                                        {allergen}
                                        {customAllergens.includes(allergen) && ' (custom)'}
                                    </label>
                                </div>
                            ))}
                        </div>
                    )}
                </div>

                {/* Selected allergens tags */}
                {allergens.length > 0 && (
                    <div className={styles.selectedAllergens}>
                        {allergens.map(allergen => (
                            <div key={allergen} className={styles.allergenTag}>
                                {allergen}
                                <button onClick={() => handleAllergenChange(allergen)}>
                                    ✕
                                </button>
                            </div>
                        ))}
                    </div>
                )}

                {/* Add custom allergen */}
                <div className={styles.addCustomContainer}>
                    <input
                        type="text"
                        placeholder="Add custom allergen..."
                        value={newAllergen}
                        onChange={(e) => setNewAllergen(e.target.value)}
                        onKeyPress={(e) => e.key === 'Enter' && handleAddCustomAllergen()}
                    />
                    <button onClick={handleAddCustomAllergen}>Add</button>
                </div>

                {customAllergens.length > 0 && (
                    <div style={{ marginTop: '1rem' }}>
                        <p style={{ fontSize: '0.9rem', color: '#666', marginBottom: '0.5rem' }}>
                            Custom allergens:
                        </p>
                        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem' }}>
                            {customAllergens.map(allergen => (
                                <div
                                    key={allergen}
                                    style={{
                                        background: '#f0f0f0',
                                        padding: '0.4rem 0.8rem',
                                        borderRadius: '1rem',
                                        display: 'flex',
                                        alignItems: 'center',
                                        gap: '0.5rem',
                                        fontSize: '0.9rem'
                                    }}
                                >
                                    {allergen}
                                    <button
                                        onClick={() => handleRemoveCustomAllergen(allergen)}
                                        style={{
                                            background: 'none',
                                            border: 'none',
                                            cursor: 'pointer',
                                            fontSize: '1rem',
                                            padding: 0,
                                            color: '#999'
                                        }}
                                    >
                                        ✕
                                    </button>
                                </div>
                            ))}
                        </div>
                    </div>
                )}
            </div>

            {/* Expiry Warning Section */}
            <div className={styles.section}>
                <h2>Expiry Warning</h2>
                <div className={styles.settingRow}>
                    <label className={styles.settingLabel}>
                        Show warning if item expires within:
                    </label>
                    <div className={styles.settingInput}>
                        <input
                            type="number"
                            min="1"
                            max="30"
                            value={expiryWarningDays}
                            onChange={handleExpiryWarningChange}
                        />
                        <span>days</span>
                    </div>
                </div>
            </div>
        </div>
    )
}