import { backendServer } from "../CONSTANTS"
import { useEffect, useState } from "react"
import styles from "../styles/Inventory.module.css"
import Loading from "../components/loading";

interface InventoryCardType {
    id: string,
    name: string,
    expiry_date: string,
    date_added?: string
}

type SortKey = 'name' | 'expiry_date' | 'date_added';
type SortOrder = 'asc' | 'desc';

async function fetchInventoryFromAPI() {
    try {
        const response = await fetch(`http://${backendServer}/api/inventory`)
        if (!response.ok) {
            throw new Error(`API error: ${response.status}`)
        }
        const data = await response.json()
        return data
    } catch (error) {
        console.error('Failed to fetch inventory:', error)
        return []
    }
}

async function addInventoryItem(item: Omit<InventoryCardType, 'id' | 'date_added'>) {
    try {
        const response = await fetch(`http://${backendServer}/api/inventory`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(item)
        })
        if (!response.ok) {
            throw new Error(`API error: ${response.status}`)
        }
        return await response.json()
    } catch (error) {
        console.error('Failed to add inventory item:', error)
        throw error
    }
}

async function deleteInventoryItem(id: string) {
    try {
        const response = await fetch(`http://${backendServer}/api/inventory/${id}`, {
            method: 'DELETE'
        })
        if (!response.ok) {
            throw new Error(`API error: ${response.status}`)
        }
        return true
    } catch (error) {
        console.error('Failed to delete inventory item:', error)
        throw error
    }
}

function isValidDate(dateString: string): boolean {
    const date = new Date(dateString)
    return !isNaN(date.getTime())
}

// Check if expiry date is within warning threshold
function isExpiringSoon(expiryDateString: string, warningDays: number): boolean {
    const expiryDate = new Date(expiryDateString);
    expiryDate.setHours(0, 0, 0, 0);
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    const warningDate = new Date(today.getTime() + warningDays * 24 * 60 * 60 * 1000);
    console.log("CHECK:", warningDate, today, expiryDate)
    return expiryDate <= warningDate && expiryDate >= today;
}

// Check if expired
function isExpired(expiryDateString: string): boolean {
    const expiryDate = new Date(expiryDateString);
    expiryDate.setHours(0, 0, 0, 0);
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    return expiryDate < today;
}

function AddItemPopup({ isOpen, onClose, onAdd }: {
    isOpen: boolean;
    onClose: () => void;
    onAdd: (item: { name: string; expiry_date: string }) => void;
}) {
    const [name, setName] = useState('');
    const [expiryDate, setExpiryDate] = useState('');
    const [error, setError] = useState('');

    const handleSubmit = () => {
        if (!name.trim()) {
            setError('Item name is required');
            return;
        }
        if (!expiryDate || !isValidDate(expiryDate)) {
            setError('Valid expiry date is required');
            return;
        }
        
        onAdd({ name: name.trim(), expiry_date: expiryDate });
        setName('');
        setExpiryDate('');
        setError('');
        onClose();
    };

    const handleCancel = () => {
        setName('');
        setExpiryDate('');
        setError('');
        onClose();
    };

    if (!isOpen) return null;

    return (
        <div className={styles.popupOverlay}>
            <div className={styles.popup}>
                <h2>Add New Item</h2>
                {error && <div className={styles.error}>{error}</div>}
                <div className={styles.formGroup}>
                    <label>Item Name:</label>
                    <input
                        type="text"
                        value={name}
                        onChange={(e) => setName(e.target.value)}
                        placeholder="Enter item name"
                    />
                </div>
                <div className={styles.formGroup}>
                    <label>Expiry Date:</label>
                    <input
                        type="date"
                        value={expiryDate}
                        onChange={(e) => setExpiryDate(e.target.value)}
                    />
                </div>
                <div className={styles.popupButtons}>
                    <button className={styles.cancelButton} onClick={handleCancel}>
                        Cancel
                    </button>
                    <button className={styles.addButton} onClick={handleSubmit}>
                        Add Item
                    </button>
                </div>
            </div>
        </div>
    );
}

function InventoryRow({ inventoryProps, onDelete, warningDays }: {
    inventoryProps: InventoryCardType;
    onDelete: (id: string) => void;
    warningDays: number;
}) {
    const expired = isExpired(inventoryProps.expiry_date);
    const expiring = !expired && isExpiringSoon(inventoryProps.expiry_date, warningDays);
    console.log(inventoryProps.name, expiring)
    const expiryClass = expired ? styles.expired : (expiring ? styles.warning : '');

    const handleDelete = () => {
        onDelete(inventoryProps.id)
    };

    return (
        <div className={styles.row}>
            <h1 className={styles.itemName}>{inventoryProps.name}</h1>
            <div className={styles.rowRight}>
                <p className={`${styles.expiryDate} ${expiryClass}`}>
                    {inventoryProps.expiry_date}
                </p>
                <button className={styles.deleteButton} onClick={handleDelete}>
                    ✕
                </button>
            </div>
        </div>
    )
}

export default function Inventory() {
    const [inventory, setInventory] = useState<InventoryCardType[] | null>(null);
    const [sortKey, setSortKey] = useState<SortKey>('name');
    const [sortOrder, setSortOrder] = useState<SortOrder>('asc');
    const [isPopupOpen, setIsPopupOpen] = useState(false);
    const [warningDays, setWarningDays] = useState(parseInt(localStorage.getItem('expiryWarningDays') || '3'));

    useEffect(() => {
        fetchInventoryFromAPI().then(data => setInventory(data))
        
        // Listen for storage changes to update warning days
        const handleStorageChange = () => {
            const newWarningDays = parseInt(localStorage.getItem('expiryWarningDays') || '3');
            setWarningDays(newWarningDays);
        };
        
        window.addEventListener('storage', handleStorageChange);
        window.addEventListener('settingsChanged', handleStorageChange);
        
        return () => {
            window.removeEventListener('storage', handleStorageChange);
            window.removeEventListener('settingsChanged', handleStorageChange);
        };
    }, [])

    const handleAddItem = async (item: { name: string; expiry_date: string }) => {
        try {
            const newItem = await addInventoryItem(item);
            setInventory(prev => prev ? [...prev, newItem] : [newItem]);
        } catch (error) {
            alert('Failed to add item. Please try again.');
        }
    };

    const handleDeleteItem = async (id: string) => {
        try {
            await deleteInventoryItem(id);
            setInventory(prev => prev ? prev.filter(item => item.id !== id) : null);
        } catch (error) {
            alert('Failed to delete item. Please try again.');
        }
    };

    // Sort inventory based on current sort settings
    const sortedInventory = inventory ? [...inventory].sort((a, b) => {
        let firstValue: any;
        let secondValue: any;

        if (sortKey === 'name') {
            firstValue = a.name.toLowerCase();
            secondValue = b.name.toLowerCase();
        } else if (sortKey === 'expiry_date') {
            firstValue = new Date(a.expiry_date).getTime();
            secondValue = new Date(b.expiry_date).getTime();
        } else if (sortKey === 'date_added') {
            firstValue = a.date_added ? new Date(a.date_added).getTime() : 0;
            secondValue = b.date_added ? new Date(b.date_added).getTime() : 0;
        }

        if (firstValue < secondValue) return sortOrder === 'asc' ? -1 : 1;
        if (firstValue > secondValue) return sortOrder === 'asc' ? 1 : -1;
        return 0;
    }) : null;

    const handleSort = (key: SortKey) => {
        if (sortKey === key) {
            setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc');
        } else {
            setSortKey(key);
            setSortOrder('asc');
        }
    };

    return (
        <div>
            <h1 className={styles.pageName}>My inventory</h1>
            {inventory ? (
                <>
                    <div className={styles.sortControls}>
                        <button
                            className={`${styles.sortButton} ${sortKey === 'name' ? styles.active : styles.inactive}`}
                            onClick={() => handleSort('name')}
                        >
                            Name {sortKey === 'name' && (sortOrder === 'asc' ? '↑' : '↓')}
                        </button>
                        <button
                            className={`${styles.sortButton} ${sortKey === 'expiry_date' ? styles.active : styles.inactive}`}
                            onClick={() => handleSort('expiry_date')}
                        >
                            Expiry Date {sortKey === 'expiry_date' && (sortOrder === 'asc' ? '↑' : '↓')}
                        </button>
                        <button
                            className={`${styles.sortButton} ${sortKey === 'date_added' ? styles.active : styles.inactive}`}
                            onClick={() => handleSort('date_added')}
                        >
                            Date Added {sortKey === 'date_added' && (sortOrder === 'asc' ? '↑' : '↓')}
                        </button>
                    </div>
                    <div className={styles.container}>
                        {sortedInventory?.map(item => (
                            <InventoryRow 
                                key={item.id} 
                                inventoryProps={item} 
                                onDelete={handleDeleteItem}
                                warningDays={warningDays}
                            />
                        ))}
                    
                    <button 
                        className={styles.addItemButton}
                        onClick={() => setIsPopupOpen(true)}
                    >
                        + Add Item
                    </button>
                    </div>
                    <AddItemPopup 
                        isOpen={isPopupOpen}
                        onClose={() => setIsPopupOpen(false)}
                        onAdd={handleAddItem}
                    />
                </>
            ) : (
                <div>
                    <Loading message={"Fetching Inventory..."}/>
                </div>
            )}
        </div>
    )
}