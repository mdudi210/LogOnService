export function MessageBanner({ type, message }: { type: 'success' | 'error'; message: string | null }) {
  if (!message) {
    return null;
  }

  return <div className={`banner ${type}`}>{message}</div>;
}
