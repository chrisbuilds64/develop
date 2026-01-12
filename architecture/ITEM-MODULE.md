# Item Module Architecture

**Version:** 1.0
**Status:** Approved
**Date:** January 12, 2026

---

## 1. Vision

Abstrakte Basis für alle datenhaltenden Anwendungen. Ein "Item" repräsentiert jede Form von strukturierter Information.

**Ziel:** Generisches System, das mit minimalen Erweiterungen spezialisierte Manager abbildet (YouTube-Links, Adressbuch, Aufgabenlisten).

---

## 2. Core Model

### Item

```
Item
├── id: UUID
├── owner_id: string              # Besitzer (User-ID)
├── label: string                 # Anzeigename für Listen
├── content_type: string          # "text/plain", "media/youtube", "app/address"
├── payload: JSONB                # Typ-spezifische Daten
├── tags: string[]                # Einfache Tag-Liste
├── created_at: timestamp
├── updated_at: timestamp
└── deleted_at: timestamp         # Soft-Delete
```

### Payload-Beispiele

**YouTube-Link:**
```json
{
  "url": "https://youtube.com/watch?v=xxx",
  "video_id": "xxx",
  "title": "Workout Video",
  "thumbnail_url": "https://..."
}
```

**Adresse:**
```json
{
  "first_name": "Max",
  "last_name": "Mustermann",
  "email": "max@example.com",
  "photo_base64": "..."
}
```

---

## 3. Design-Entscheidungen

| Thema | Entscheidung | Begründung |
|-------|--------------|------------|
| Payload | Hybrid: Core-Felder normalisiert, Rest in JSONB | Query-Performance auf Core, Flexibilität für Typ-Daten |
| Tags | Einfaches String-Array | KISS - Hierarchie später wenn nötig |
| Soft-Delete | Ja, mit deleted_at | Recovery-Option, Audit-Trail |
| Multi-Tenancy | owner_id pro Item | User-Isolation, Sharing später |

---

## 4. API (Phase 1)

```
POST   /items                    # Create
GET    /items                    # List (filter: tags, content_type)
GET    /items/{id}               # Get
PUT    /items/{id}               # Update
DELETE /items/{id}               # Soft-Delete
```

---

## 5. Roadmap (Design for Extension)

### Vorbereitet aber NICHT gebaut:

| Feature | Erweiterungspunkt | Wann |
|---------|-------------------|------|
| **Relations** | `item_relations` Tabelle, relation_type enum | Wenn hierarchische Strukturen gebraucht |
| **Assignments** | `item_assignments` Tabelle | Wenn Task-Management gebraucht |
| **Config-Modul** | Layout-Hints, Type-Registry | Wenn Frontend dynamische Layouts braucht |
| **Hierarchische Tags** | Tag-Tabelle mit parent_id | Wenn einfache Tags nicht reichen |
| **Team-Sharing** | Workspace/Team-Konzept | Wenn Multi-User Collaboration gebraucht |

### Relations (geplant)
```
ItemRelation
├── source_id → target_id
├── relation_type: "parent" | "link" | "reference"
└── position: integer (Sortierung)
```

### Assignments (geplant)
```
ItemAssignment
├── item_id, assignee_id
├── due_date, reminder_at
└── status: "pending" | "completed"
```

### Config-Modul (geplant)
- Type-Registry: Schema pro content_type
- Layout-Hints: Frontend-Darstellung pro Type
- Validierung: Payload-Validierung pro Type

### Offline-Sync (geplant - Mobile)
```
Mobile App Architecture:
├── UI Layer
├── Local Repository (SQLite/Hive)
│   └── Sync Queue (pending changes)
├── Sync Service
│   ├── Conflict Resolution
│   └── Background Sync
└── API Client → Backend

Sync-Strategie:
- Items lokal speichern (Device SQLite)
- Änderungen in Queue bei Offline
- Auto-Sync bei Verbindung
- Konfliktauflösung via updated_at (Last-Write-Wins)
- Optional: Merge für komplexe Fälle
```

**Wichtig:** Mobile Apps müssen offline funktionieren. Sync ist kein Nice-to-Have.

---

## 6. Implementierung Phase 1

**Scope:**
- Item CRUD mit Payload
- Einfache Tags (String-Array)
- Filter nach tags, content_type
- Soft-Delete

**Nicht in Phase 1:**
- Relations
- Assignments
- Config-Modul
- Hierarchische Tags

---

**Status:** Phase 1 implementiert (2026-01-12)
