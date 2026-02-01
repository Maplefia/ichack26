import { isPermissionGranted, requestPermission, sendNotification } from '@tauri-apps/plugin-notification';
import { backendServer } from '../CONSTANTS';

export async function checkExpiryAndNotify() {
    try {
        console.log('[Notifications] Starting expiry check...');
        
        // Fetch latest inventory
        const response = await fetch(`http://${backendServer}/api/inventory`);
        const inventory = await response.json();
        console.log('[Notifications] Fetched inventory:', inventory);
        
        const warningDays = parseInt(localStorage.getItem('expiryWarningDays') || '3');
        console.log('[Notifications] Warning days:', warningDays);
        
        const today = new Date();
        today.setHours(0, 0, 0, 0); // Reset time to midnight for accurate date comparison
        const warningDate = new Date(today.getTime() + warningDays * 24 * 60 * 60 * 1000);
        console.log('[Notifications] Today:', today, 'Warning date:', warningDate);
        
        const expiredItems: any[] = [];
        const expiringSoonItems: any[] = [];
        
        inventory.forEach((item: any) => {
            const expiry = new Date(item.expiry_date);
            expiry.setHours(0, 0, 0, 0); // Reset time to midnight
            
            if (expiry < today) {
                expiredItems.push(item);
                console.log(`[Notifications] Item ${item.name} has EXPIRED (${expiry})`);
            } else if (expiry <= warningDate) {
                expiringSoonItems.push(item);
                console.log(`[Notifications] Item ${item.name} is EXPIRING SOON (${expiry})`);
            }
        });
        
        console.log('[Notifications] Expired items:', expiredItems);
        console.log('[Notifications] Expiring soon items:', expiringSoonItems);
        
        if (expiredItems.length > 0 || expiringSoonItems.length > 0) {
            console.log('[Notifications] Checking permissions...');
            let permissionGranted = await isPermissionGranted();
            console.log('[Notifications] Initial permission granted:', permissionGranted);
            
            if (!permissionGranted) {
                console.log('[Notifications] Requesting permission...');
                const permission = await requestPermission();
                console.log('[Notifications] Permission response:', permission);
                permissionGranted = permission === 'granted';
            }
            
            // Build notification message
            let title = '';
            let body = '';
            
            if (expiredItems.length > 0 && expiringSoonItems.length > 0) {
                title = 'Pantry Alert!';
                body = `EXPIRED: ${expiredItems.map((i: any) => i.name).join(', ')}. EXPIRING SOON: ${expiringSoonItems.map((i: any) => i.name).join(', ')}`;
            } else if (expiredItems.length > 0) {
                title = 'Items Have Expired!';
                body = `${expiredItems.length} item${expiredItems.length > 1 ? 's' : ''}: ${expiredItems.map((i: any) => i.name).join(', ')}`;
            } else {
                title = 'Items Expiring Soon!';
                body = `${expiringSoonItems.length} item${expiringSoonItems.length > 1 ? 's' : ''}: ${expiringSoonItems.map((i: any) => i.name).join(', ')}`;
            }
            
            // Try to send notification regardless - Android permission check can be unreliable
            try {
                console.log('[Notifications] Attempting to send notification...');
                await sendNotification({ title, body });
                console.log('[Notifications] Notification sent successfully!');
            } catch (notifError) {
                console.error('[Notifications] Failed to send notification:', notifError);
                console.log('[Notifications] This may be a permission issue. Check Android app settings.');
            }
        } else {
            console.log('[Notifications] No expiring or expired items found');
        }
    } catch (error) {
        console.error('[Notifications] Failed to check expiry:', error);
    }
}