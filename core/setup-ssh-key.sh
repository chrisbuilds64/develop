#!/bin/bash
# SSH Key Setup für Strato VPS
# Generiert einen neuen SSH-Key für sichere Server-Verbindung

set -e

echo "🔐 SSH Key Setup für Strato VPS"
echo "================================"
echo ""

# Key-Pfad
KEY_PATH="$HOME/.ssh/strato_vps"

# Prüfen ob Key bereits existiert
if [ -f "$KEY_PATH" ]; then
    echo "⚠️  SSH Key existiert bereits: $KEY_PATH"
    read -p "Überschreiben? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "❌ Abgebrochen."
        exit 1
    fi
fi

# SSH Key generieren
echo "🔨 Generiere SSH Key..."
ssh-keygen -t ed25519 -C "chrisbuilds64-strato-vps" -f "$KEY_PATH" -N ""

echo ""
echo "✅ SSH Key erfolgreich generiert!"
echo ""
echo "📁 Private Key: $KEY_PATH"
echo "📁 Public Key:  $KEY_PATH.pub"
echo ""
echo "📋 Public Key Inhalt (für Strato Portal):"
echo "=========================================="
cat "$KEY_PATH.pub"
echo "=========================================="
echo ""
echo "📝 Nächste Schritte:"
echo "1. Kopiere den Public Key (oben)"
echo "2. Füge ihn im Strato Portal ein (Server-Setup oder ~/.ssh/authorized_keys)"
echo "3. Teste die Verbindung mit:"
echo "   ssh -i $KEY_PATH root@YOUR_SERVER_IP"
echo ""
