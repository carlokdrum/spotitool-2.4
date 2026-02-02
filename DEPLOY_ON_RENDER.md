# Cómo Desplegar SpotiTool V2.4 en Render

Esta carpeta contiene todo lo necesario para desplegar tu aplicación como un "Web Service" en Render.

## Pasos para Desplegar

1. **Sube este código a GitHub/GitLab**
    * Crea un nuevo repositorio (puedes llamarlo `spotitool-render`).
    * Sube todos los archivos de esta carpeta (`Spotitool website V2.4`) a ese repositorio.

2. **Crea una cuenta en Render.com**
    * Ve a [Render.com](https://render.com) y regístrate.

3. **Conecta tu Repositorio**
    * En el panel de Render, haz clic en **"New +"** y selecciona **"Blueprint"**.
    * Conecta tu cuenta de GitHub/GitLab y selecciona el repositorio que acabas de crear.
    * Render detectará automáticamente el archivo `render.yaml` y configurará todo por ti.

4. **Configura las Variables de Entorno**
    * Render te pedirá que confirmes las variables.
    * EL sistema generará automáticamente una `SECRET_KEY` segura.
    * **IMPORTANTE:** Deberás introducir manualmente tus credenciales de Spotify:
        * `SPOTIPY_CLIENT_ID`: Tu ID de cliente de Spotify.
        * `SPOTIPY_CLIENT_SECRET`: Tu secreto de cliente.
        * `SPOTIPY_REDIRECT_URI`: Deberás actualizar esto a la URL que Render te asigne (ej: `https://spotitool-v2.onrender.com/callback`).

5. **¡Listo!**
    * Render construirá la aplicación e instalará las dependencias. En unos minutos, tu web estará online.

## Nota sobre "Sitio Estático" vs "Web Service"

Aunque solicitaste un "sitio estático", esta aplicación requiere un servidor (Python) para procesar el inicio de sesión con Spotify y ocultar tus claves secretas. Por eso se configura como un **Web Service**. Esto es más potente y seguro.
