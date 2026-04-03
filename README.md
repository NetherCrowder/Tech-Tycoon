# Tech Tycoon: Virtual Defense 🛡️💻

**Tech Tycoon** es un híbrido innovador entre el género **Tycoon** (Gestión de Recursos) y **Tower Defense** (Defensa de Torres) ambientado en un entorno de ciberseguridad virtual. El objetivo es construir y optimizar una red de reactores para generar energía y créditos mientras defiendes el **Núcleo Central** de incursiones de malware persistentes (Ghosnets).

---

## 🚀 Arquitectura del Proyecto

El juego utiliza una arquitectura moderna desacoplada:

- **Backend**: [FastAPI](https://fastapi.tiangolo.com/) (Python 3.12+) maneja el motor de física, la simulación económica a 10 ticks/segundo y la persistencia del estado en memoria.
- **Frontend**: Una interfaz **SPA (Single Page Application)** construida con HTML5, CSS3 (Glassmorphism) y Vanilla JavaScript. Utiliza interpolación de movimiento basada en GPU para los enemigos y un sistema de renderizado radial.
- **Data Engine**: Modelos de datos extensibles basados en JSON y **Pydantic** para definir activos (generadores, defensas y mejoras).

---

## 🛠️ Mecánicas Principales

### 1. Economía y Escalado (Balance v2.0)
El juego implementa sistemas de costos diferenciados para obligar a la especialización estratégica:
- **Generadores**: Escalado exponencial de **1.15x** (enfocado en niveles).
- **Defensas**: Escalado de **1.4x** (enfocado en unidades limitadas).
- **Moneda Especial (W-Hex)**: Obtenida mediante victorias de oleadas.
  - *Fórmula*: `W-Hex = round(5 * Fase^0.7 * log2(Prestigio + 1))`

### 2. Sistema de Combate y Oleadas
- **IA de Amenaza**: Los enemigos priorizan defensas de tipo eléctrico si están en rango antes de atacar el Core.
- **Health System**: Las defensas tienen puntos de vida y pueden ser destruidas, requiriendo reconstrucción estratégica.
- **Nivel de Amenaza**: Un medidor dinámico que, al llegar al 100%, libera una nueva horda de malware.

### 3. Interfaz de Usuario (HUD/UI)
- **Abreviatura de Grandes Reales**: Notación científica compacta (100 -> 1K -> 1M) para manejar economías masivas.
- **Catálogo Dinámico**: Muestra estadísticas en tiempo real (Producción + Cooldown) recalculadas con multiplicadores de tecnología.

---

## 📦 Instalación y Ejecución

Para correr el proyecto localmente:

1. **Clonar el Repositorio**:
   ```bash
   git clone https://github.com/tu-usuario/Tech-Tycoon.git
   cd Tech-Tycoon
   ```

2. **Configurar el Entorno**:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # (o .venv\Scripts\activate en Windows)
   pip install -r requirements.txt
   ```

3. **Iniciar el Servidor**:
   ```bash
   python main.py
   ```
   *El servidor correrá en `http://localhost:8000`*

---

## 🗺️ Hoja de Ruta (Próximos Pasos)

- [ ] **Sistema de Renacimiento (Prestige)**: Implementar la lógica para resetear el progreso a cambio de multiplicadores permanentes.
- [ ] **Enemigos de Élite**: Añadir unidades con habilidades especiales (hackers, virus evasivos).
- [ ] **Múltiples Mapas**: Expandir la defensa a diferentes nodos de la red virtual.

---

## 📜 Licencia
Este proyecto es de código abierto bajo la licencia MIT.

*Desarrollado como prototipo de alto rendimiento para Tech Tycoon Combat Progression.*
