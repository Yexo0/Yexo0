# Cartes du profil

Les images du profil (`assets/*.svg`) sont générées par `build.py` à partir de `profile.yml`.
Le texte est converti en tracés vectoriels avec les polices du site (Inter Tight pour les titres,
Geist pour le texte) : le rendu est identique partout, sans dépendre des polices du visiteur.

## Modifier le contenu

1. Modifie `src/profile.yml` (directement sur github.com si tu veux).
2. Pousse sur `main` : l'action **Build profile cards** régénère les SVG et les commit toute seule.

En local :

```bash
python -m venv .venv
.venv/bin/pip install -r src/requirements.txt
.venv/bin/python src/build.py
```

La date du bloc « Now » (`{month}`) prend le mois de la génération : elle sert de « mis à jour le ».

## Ce qui se règle où

| Quoi | Où |
|------|----|
| Textes, stats, projets, stack | `src/profile.yml` |
| Couleurs (rouge Valorant, fonds, gris) | constantes en haut de `src/build.py` |
| Liens des boutons et des cartes | `README.md` (racine) |
| Icônes de marque disponibles | `src/icons.json` |

## Licences

- Inter Tight et Geist : SIL Open Font License 1.1 (`src/fonts/OFL-*.txt`).
- Icônes de marque : [Simple Icons](https://simpleicons.org), CC0. Les marques restent à leurs propriétaires.
- Icônes au trait : dessinées dans le style de [Lucide](https://lucide.dev), licence ISC.
