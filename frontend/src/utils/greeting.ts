const DISPLAY_NAME_KEY = 'agent.displayName';

function timeGreeting(date: Date): string {
    const hour = date.getHours();
    if (hour >= 5 && hour < 12) return 'Good morning';
    if (hour >= 12 && hour < 17) return 'Good afternoon';
    return 'Good evening';
}

export function getGreeting(now: Date = new Date()): string {
    const greeting = timeGreeting(now);
    const name = localStorage.getItem(DISPLAY_NAME_KEY)?.trim();
    return name ? `${greeting}, ${name}` : greeting;
}
