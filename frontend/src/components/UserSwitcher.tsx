// Auswahl der handelnden Person (Demo ohne Login).
// Die Rechte prüft das Backend – die Auswahl hier legt nur fest, wer handelt.

import type { User } from "../types";

interface Props {
  users: User[];
  userId: string;
  onChange: (id: string) => void;
}

export function UserSwitcher({ users, userId, onChange }: Props) {
  const user = users.find((u) => u.id === userId);
  return (
    <label className="user-switch" title="Acting person (demo, no login)">
      <span className={`user-switch__avatar user-switch__avatar--${user?.role ?? "none"}`} aria-hidden>
        {user?.name[0] ?? "?"}
      </span>
      <select value={userId} onChange={(e) => onChange(e.target.value)} aria-label="Acting person">
        {users.map((u) => (
          <option key={u.id} value={u.id}>
            {u.name} · {u.role_label}
            {u.permissions.length === 0 ? " (read-only)" : ""}
          </option>
        ))}
      </select>
    </label>
  );
}
