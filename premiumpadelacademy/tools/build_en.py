#!/usr/bin/env python3
"""Generate the English site at site-v2/en/ from the Spanish source pages.

Riki asked for the site in English ("Ahhh y poner la página en inglés",
2026-08-03). The chosen structure is a real /en/ subtree — four separate HTML
files with hreflang annotations and a visible ES/EN switch — not a client-side
toggle, so search engines index both languages.

The English copy is authored HERE, in TEXT/ATTR below, and applied to the
Spanish markup. That keeps one source of truth for structure: a change to the
Spanish layout re-renders into English on the next run, and no English file is
ever hand-edited. `--check` re-extracts every string from the generated pages
and fails if any Spanish text survived, so a forgotten sentence cannot ship.

Substitution is done on text nodes and on a fixed set of attributes only, never
on raw HTML, so strings like "Contacto" cannot corrupt href="contacto.html".

    python3 tools/build_en.py --build
    python3 tools/build_en.py --check

Stdlib only, to match the rest of the tooling in this repo.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent
# Set by main(); --root lets deploy/build_public.sh regenerate en/ inside build/
# AFTER the public-build transforms have run on the Spanish pages, so the English
# pages inherit the stripped reviews, the rendered partner band and the noindex
# marker instead of needing every one of those tools taught about /en/.
ROOT = PROJECT / "site-v2"
EN = ROOT / "en"

SITE_URL = "https://nexumpadel.es"

# Spanish file -> English file. Only contacto is renamed; the rest read the
# same in both languages.
ROUTES = {
    "index.html": "index.html",
    "clubs.html": "clubs.html",
    "camps.html": "camps.html",
    "contacto.html": "contact.html",
}

# Attributes whose values are prose and must be translated.
TRANSLATED_ATTRS = ("alt", "title", "aria-label", "content", "placeholder")

# Text-node and attribute translations. Every visible string on the Spanish
# site appears here; --check enforces that.
TEXT = {
    # --- chrome -------------------------------------------------------------
    "Saltar al contenido": "Skip to content",
    "Inicio": "Home",
    "Clubs": "Clubs",
    "Camps": "Camps",
    "Contacto": "Contact",
    "Nexum Padel": "Nexum Padel",
    "Email": "Email",
    "info@nexumpadel.es": "info@nexumpadel.es",
    "@nexum.padel": "@nexum.padel",
    "Colaboradores": "Partners",
    "Ubicación": "Location",
    "Marbella, España": "Marbella, Spain",
    "Academia de pádel en Marbella, España.": "Padel academy in Marbella, Spain.",
    "© 2026 Nexum Padel. Todos los derechos reservados.":
        "© 2026 Nexum Padel. All rights reserved.",

    # --- titles -------------------------------------------------------------
    "Inicio | Nexum Padel": "Home | Nexum Padel",
    "Clubs | Nexum Padel": "Clubs | Nexum Padel",
    "Camps | Nexum Padel": "Camps | Nexum Padel",
    "Contacto | Nexum Padel": "Contact | Nexum Padel",

    # --- home ---------------------------------------------------------------
    "Academia de pádel · Marbella, España": "Padel academy · Marbella, Spain",
    "Entrenamiento de pádel para todos los niveles, desde quien empieza hasta quien compite, "
    "y programas para clubes que quieren subir el nivel de su escuela.":
        "Padel coaching for every level, from your first lesson to competition, plus "
        "programmes for clubs that want to raise the standard of their academy.",
    "Los coaches": "The coaches",
    "Dos head coaches, una misma metodología.": "Two head coaches, one shared method.",
    "Trabajamos en Nueva Alcántara Club (NAC), considerado uno de los clubes de pádel más "
    "prestigiosos del mundo, con metodología desarrollada junto a M3 Academy.":
        "We work at Nueva Alcántara Club (NAC), regarded as one of the most prestigious padel "
        "clubs in the world, with a method developed alongside M3 Academy.",
    "Formación continua junto a profesionales de la élite, incorporando las metodologías más "
    "actuales y funcionales del pádel profesional.":
        "Continuous training alongside elite professionals, bringing in the most current and "
        "practical methods in professional padel.",
    "Head Coach": "Head Coach",
    "Riki Padrón": "Riki Padrón",
    "Juampi Vanella": "Juampi Vanella",
    "Más de 15 Años en la Élite": "More Than 15 Years at the Top",
    "Con más de 15 años de experiencia profesional, ofrecemos un enfoque personalizado para "
    "potenciar a jugadores de todos los niveles.":
        "With more than 15 years of professional experience, we offer a personalised approach "
        "that brings on players of every level.",
    "Durante todos estos años hemos tenido la oportunidad de trabajar y aprender junto a "
    "profesionales de gran nivel, absorbiendo diferentes metodologías, formas de entender el "
    "entrenamiento y sistemas de trabajo que han enriquecido nuestra forma de enseñar y gestionar.":
        "Over those years we have worked and learned alongside professionals at the highest "
        "level, absorbing different methods, ways of understanding training and systems of work "
        "that have shaped how we teach and how we run a programme.",
    "Esa experiencia nos ha permitido construir una metodología propia basada en la observación, "
    "el aprendizaje continuo y la aplicación práctica, con un objetivo muy claro: que cada "
    "jugador y cada club entrenen mejor de lo que entrenaban antes.":
        "That experience let us build a method of our own, based on observation, continuous "
        "learning and practical application, with one clear aim: that every player and every "
        "club trains better than they did before.",
    "¿Qué puedes esperar de trabajar con nosotros?": "What can you expect from working with us?",
    "Una experiencia totalmente adaptada a tu nivel y a tus objetivos.":
        "An experience built entirely around your level and your goals.",
    "Un entorno profesional, cercano y motivador, donde cada sesión tiene un propósito.":
        "A professional, welcoming and motivating environment where every session has a purpose.",
    "Una metodología propia aplicada de forma personalizada, tanto para jugadores que buscan "
    "competir como para quienes simplemente quieren mejorar y disfrutar del deporte.":
        "A method of our own, applied to you personally — whether you are chasing competition or "
        "simply want to improve and enjoy the game.",
    "Entrenamientos dinámicos, exigentes y divertidos, donde el aprendizaje y la motivación van "
    "siempre de la mano.":
        "Sessions that are dynamic, demanding and genuinely fun, where learning and motivation "
        "always go together.",
    "Un espacio para desconectar de la rutina, compartir la pasión por el pádel y seguir "
    "evolucionando dentro de la pista.":
        "A place to switch off from routine, share a passion for padel and keep improving on court.",
    "Un compromiso real con tu progreso, ayudándote a disfrutar más del juego mientras alcanzas "
    "tu mejor versión.":
        "A real commitment to your progress, helping you enjoy the game more as you reach your "
        "best level.",
    "Local service": "Local service",
    "Programas personalizados diseñados para potenciar el talento individual y colectivo, y "
    "llevar tu juego un nivel más allá de donde está hoy.":
        "Personalised programmes designed to bring on individual and group talent, and take your "
        "game a level beyond where it is today.",
    "Sesiones individuales y grupales adaptadas a ti.":
        "Individual and group sessions built around you.",
    "Desarrollo técnico y táctico avanzado.": "Advanced technical and tactical development.",
    "Preparación física específica para raqueta.": "Racket-specific physical preparation.",
    "Partidos dirigidos con análisis de vídeo.": "Coached matches with video analysis.",
    "Seguimiento exhaustivo de la evolución.": "Detailed tracking of your progress.",
    "Saber más": "Find out more",
    "Programas para Clubs": "Programmes for Clubs",
    "Llevamos nuestra experiencia y metodología a clubes de pádel en todo el mundo, ofreciendo "
    "programas personalizados para jugadores, entrenadores y equipos técnicos.":
        "We bring our experience and method to padel clubs worldwide, with tailored programmes "
        "for players, coaches and technical staff.",
    "Sesiones individuales y grupales para todos los niveles.":
        "Individual and group sessions for every level.",
    "Formación para entrenadores.": "Coach education.",
    "Organización de eventos exclusivos.": "Exclusive event organisation.",
    "Consultoría estratégica de actividades.": "Strategic consultancy on activities.",
    "Optimización de enseñanza interna.": "Optimisation of in-house coaching.",
    "Camps en Marbella": "Camps in Marbella",
    "Viajes y experiencias internacionales de pádel en España, con sede en Marbella.":
        "International padel trips and experiences in Spain, based in Marbella.",
    "Programas de entrenamiento personalizados.": "Personalised training programmes.",
    "Organización y gestión integral de grupos.": "End-to-end group organisation and management.",
    "Organización de partidos y experiencias.": "Matches and experiences arranged for you.",
    "Actividades físicas complementarias.": "Complementary physical activities.",
    "Información de ocio y gastronomía.": "Guidance on food and things to do.",

    # --- reviews (demo content, see HANDOFF §7) -----------------------------
    "Lo que dicen los jugadores": "What players say",
    "Reseñas de los programas": "Programme reviews",
    "Jugadores y clubes que ya han entrenado con nosotros.":
        "Players and clubs who have already trained with us.",
    "Media de": "Average of",
    "reseñas": "reviews",
    "Llevaba años estancado en el mismo nivel. En tres meses he cambiado la posición de la pala "
    "en la volea y el revés ya no es el agujero por el que me atacaban. Lo que más valoro es que "
    "cada sesión tiene un porqué.":
        "I had been stuck at the same level for years. In three months my volley grip has changed "
        "and my backhand is no longer the hole everyone attacked. What I value most is that every "
        "session has a reason behind it.",
    "Álvaro Medina": "Álvaro Medina",
    "Marbella · nivel intermedio": "Marbella · intermediate",
    "Entreno para competir y aquí encontré lo que buscaba: análisis de vídeo real, no palmaditas. "
    "Ver mis propios errores en pantalla y corregirlos a la semana siguiente ha sido la diferencia.":
        "I train to compete and here I found what I was after: real video analysis, not pats on "
        "the back. Seeing my own mistakes on screen and fixing them the following week has been "
        "the difference.",
    "Lucía Ferrer": "Lucía Ferrer",
    "Marbella · competición": "Marbella · competition",
    "Trajimos al equipo cinco días para formar a nuestros entrenadores. Volvieron con criterios "
    "unificados y una estructura de sesión que seguimos usando. La organización fue impecable; "
    "solo pediría algo más de material escrito para el staff.":
        "We brought the team over for five days to train our coaches. They came back with a "
        "shared approach and a session structure we still use. The organisation was flawless; my "
        "only ask would be a bit more written material for the staff.",
    "Tomás Nielsen": "Tomás Nielsen",
    "Director deportivo · Dinamarca": "Sporting director · Denmark",
    "Vine sola sin conocer a nadie y acabé jugando partidos nivelados todos los días. "
    "Entrenamiento serio por la mañana y Marbella por la tarde. Repito el año que viene.":
        "I came on my own not knowing anyone and ended up playing well-matched games every day. "
        "Serious training in the morning and Marbella in the afternoon. I am coming back next year.",
    "Rocío Salas": "Rocío Salas",
    "Camp en Marbella · 2026": "Camp in Marbella · 2026",
    "Como entrenador se agradece que te expliquen el porqué de cada ejercicio y no solo el qué. "
    "Me llevé una forma distinta de planificar las sesiones de mi escuela.":
        "As a coach it is refreshing to be told why each drill exists, not just what it is. I came "
        "away with a different way of planning sessions at my own academy.",
    "Nacho Beltrán": "Nacho Beltrán",
    "Entrenador · formación de staff": "Coach · staff training",
    "Organizaron todo para un grupo de ocho: pistas, niveles, partidos y hasta dónde cenar. Nos "
    "trataron como si fuéramos el único grupo de la semana.":
        "They organised everything for a group of eight: courts, levels, matches and even where to "
        "eat. They treated us as if we were the only group that week.",
    "Katrin Hoffmann": "Katrin Hoffmann",
    "Grupo internacional · temporada": "International group · season",
    "Contenido de ejemplo — pendiente de sustituir por reseñas reales.":
        "Example content — to be replaced with genuine reviews.",

    # --- contact blocks -----------------------------------------------------
    "Contacta con nosotros": "Get in touch",
    "Cuéntanos qué necesitas — clases en Marbella, un programa para tu club o un camp para tu grupo.":
        "Tell us what you need — lessons in Marbella, a programme for your club or a camp for your group.",
    "Solicita información": "Request information",
    "Escríbenos y te respondemos con una propuesta adaptada a tu nivel, tu grupo o tu club.":
        "Write to us and we will come back with a proposal built around your level, your group or "
        "your club.",
    "Solicitar programa": "Request a programme",

    # --- clubs --------------------------------------------------------------
    "Nexum Padel en tu club": "Nexum Padel at your club",
    "Aprende de los mejores. Programas intensivos de hasta 7 días para clubes de pádel en todo el mundo.":
        "Learn from the best. Intensive programmes of up to 7 days for padel clubs worldwide.",
    "Llevamos el método de uno de los clubes más prestigiosos del mundo a tus pistas.":
        "We bring the method of one of the world's most prestigious clubs to your courts.",
    "Ver programas": "See programmes",
    "Potenciar mi club": "Boost my club",
    "Programas para Club": "Club Programmes",
    "Coaching en pista": "On-court coaching",
    "Sesiones individuales y grupales para todos los niveles con enfoque en desarrollo técnico y "
    "táctico intensivo.":
        "Individual and group sessions for every level, focused on intensive technical and "
        "tactical development.",
    "Formación Entrenadores": "Coach Education",
    "Clínics técnicos para el staff, planificación de sesiones y actualización en nuevas "
    "metodologías de enseñanza.":
        "Technical clinics for staff, session planning and an update on new teaching methods.",
    "Eventos y Masterclass": "Events and Masterclasses",
    "Jornadas abiertas a todos los socios, partidos de exhibición y actividades exclusivas para "
    "dinamizar la vida del club.":
        "Open days for every member, exhibition matches and exclusive activities that bring the "
        "club to life.",
    "Consultoría": "Consultancy",
    "Optimización de programas deportivos y creación de nuevas estructuras para mejorar los "
    "servicios de su club.":
        "Optimising sporting programmes and building new structures to improve what your club "
        "offers.",
    "Dinámica de impacto": "How the work lands",
    "Estrategia integral diseñada para transformar el rendimiento deportivo de su institución.":
        "A complete strategy designed to transform the sporting performance of your organisation.",
    "Diagnóstico inicial": "Initial assessment",
    "Evaluación de la estructura actual para personalizar el programa según los objetivos del centro.":
        "A review of the current setup so the programme fits the centre's own objectives.",
    "Desarrollo técnico": "Technical development",
    "Sesiones de perfeccionamiento biomecánico y ajuste táctico para jugadores de todas las categorías.":
        "Biomechanical refinement and tactical adjustment for players in every category.",
    "Formación de staff": "Staff training",
    "Capacitación técnica para entrenadores locales, unificando criterios y herramientas de trabajo.":
        "Technical training for local coaches, aligning their approach and their tools.",
    "Gestión de socio": "Member engagement",
    "Implementación de actividades que aumentan el valor percibido y la fidelización de la membresía.":
        "Activities that raise perceived value and keep members coming back.",
    "Plan de ejecución": "Delivery plan",
    "Establecimiento de una hoja de ruta clara para la mejora continua de la escuela de pádel.":
        "A clear roadmap for the continuous improvement of the padel academy.",
    "Programas 100% personalizados": "Programmes built 100% around you",
    "Impacto deportivo": "Sporting impact",
    "Cada visita se diseña a medida según el club: programa propio, objetivos claros y resultados "
    "medibles.":
        "Every visit is designed around the club: its own programme, clear objectives and "
        "measurable results.",
    "Visión estratégica": "Strategic view",
    "Enseñanza y disfrute en la misma sesión, para perfiles de jugador muy distintos.":
        "Teaching and enjoyment in the same session, for very different kinds of player.",
    "Innovación y servicios": "Innovation and services",
    "Ayudamos a dirección a crear servicios nuevos y a sacar más partido a los que ya existen.":
        "We help management create new services and get more out of the ones already running.",
    "Cuéntanos cómo es tu club y te preparamos una propuesta a medida.":
        "Tell us about your club and we will put together a tailored proposal.",
    "Potencia tu club": "Boost your club",
    "Programas de hasta 7 días para jugadores, entrenadores y equipos técnicos, adaptados a la "
    "estructura de cada entidad.":
        "Programmes of up to 7 days for players, coaches and technical staff, adapted to each "
        "organisation's structure.",

    # --- camps --------------------------------------------------------------
    "Sube tu nivel en el Mediterráneo con programas de pádel diseñados a la medida de tu grupo, "
    "sea cual sea el punto de partida.":
        "Raise your game on the Mediterranean with padel programmes built around your group, "
        "whatever your starting point.",
    "Pedir información": "Request information",
    "Entrena, descubre y disfruta": "Train, explore and enjoy",
    "Entrena en instalaciones premium, mejora tu rendimiento con entrenadores especializados y "
    "disfruta del estilo de vida que ha convertido Marbella en un referente internacional del "
    "deporte.":
        "Train at premium facilities, improve with specialist coaches and enjoy the lifestyle that "
        "has made Marbella an international sporting destination.",
    "Nuestra metodología": "Our method",
    "Tres pilares. Nada más, y ninguno de menos.": "Three pillars. No more, and none of them missing.",
    "Técnico": "Technical",
    "Perfeccionar cada golpe hasta que aguante bajo presión.":
        "Refining every shot until it holds up under pressure.",
    "Táctico": "Tactical",
    "Leer el juego y decidir mejor y más rápido que el rival.":
        "Reading the game and deciding better and faster than your opponent.",
    "Físico": "Physical",
    "Que el cuerpo responda a lo que le pides dentro de la pista.":
        "Making sure your body answers what you ask of it on court.",
    "¿Qué incluye la experiencia?": "What does the experience include?",
    "Entrenamiento en pista": "On-court training",
    "Sesiones intensivas diseñadas para perfeccionar técnica y táctica en el entorno de Marbella.":
        "Intensive sessions designed to sharpen technique and tactics in the Marbella setting.",
    "Experiencia deportiva": "Sporting experience",
    "Inmersión total en el mundo del pádel de la zona con competiciones amistosas y partidos "
    "nivelados.":
        "Full immersion in the local padel scene, with friendly competitions and well-matched games.",
    "Descubre Marbella": "Discover Marbella",
    "Asesoramiento para disfrutar de la mejor oferta gastronómica y de ocio en uno de los destinos "
    "más exclusivos de Europa.":
        "Recommendations for the best food and nightlife in one of Europe's most exclusive "
        "destinations.",
    "Programas personalizados": "Tailored programmes",
    "Adaptamos la experiencia a las necesidades específicas de tu grupo o club deportivo.":
        "We shape the experience around the specific needs of your group or sports club.",
    "Preguntas Frecuentes": "Frequently Asked Questions",
    "¿Qué niveles aceptáis en vuestros programas?": "Which levels do you accept on your programmes?",
    "Aceptamos jugadores de todos los niveles, desde principiantes que buscan aprender las bases "
    "hasta jugadores avanzados y de competición que desean perfeccionar su técnica y su táctica.":
        "We accept players of every level, from beginners learning the basics to advanced and "
        "competitive players looking to refine their technique and tactics.",
    "¿Es necesario traer mi propio material?": "Do I need to bring my own equipment?",
    "Recomendamos que los jugadores traigan su propia pala para mayor comodidad, pero disponemos "
    "de material de alta calidad para alquilar o prestar si es necesario durante la experiencia.":
        "We recommend bringing your own racket for comfort, but we have high-quality equipment to "
        "hire or lend during the experience if you need it.",
    "¿Cómo se gestionan los Camps en Marbella para grupos?":
        "How are the Marbella Camps managed for groups?",
    "Ofrecemos una gestión integral que incluye el diseño del programa deportivo, la organización "
    "de partidos, actividades complementarias y recomendaciones locales. Trabajamos estrechamente "
    "con los responsables del grupo para asegurar una estancia perfecta en Marbella.":
        "We handle everything: designing the sporting programme, arranging matches, complementary "
        "activities and local recommendations. We work closely with whoever leads the group to "
        "make the stay in Marbella run perfectly.",
    "Dinos cuántos sois y qué fechas manejáis, y preparamos el camp a medida.":
        "Tell us how many of you there are and which dates you have in mind, and we will build the "
        "camp around it.",
    "Camps a medida": "Tailored camps",
    "Programa deportivo, organización de partidos, actividades complementarias y recomendaciones "
    "locales — gestionado de principio a fin.":
        "Sporting programme, matches, complementary activities and local recommendations — managed "
        "from start to finish.",

    # --- contacto page ------------------------------------------------------
    "Nexum Padel · Marbella": "Nexum Padel · Marbella",
    "Solicita Información": "Request Information",
    "Cuéntanos qué necesitas: clases en Marbella para tu nivel, un programa para tu club o un camp "
    "para tu grupo.":
        "Tell us what you need: lessons in Marbella for your level, a programme for your club or a "
        "camp for your group.",
    "Cuéntanos tu proyecto": "Tell us about your project",
    "Nombre": "Name",
    "Mensaje": "Message",
    "Se abrirá tu aplicación de correo con el mensaje listo para enviar.":
        "Your mail app will open with the message ready to send.",
}

# Attribute-only strings (alt text, aria-labels, meta descriptions).
ATTR = {
    "width=device-width, initial-scale=1": "width=device-width, initial-scale=1",
    "website": "website",
    "Nexum Padel — inicio": "Nexum Padel — home",
    "Abrir menú": "Open menu",
    "Principal": "Main",
    "España": "Spain",
    "Argentina": "Argentina",
    "5 de 5 estrellas": "5 out of 5 stars",
    "4 de 5 estrellas": "4 out of 5 stars",
    "Instagram de Nexum Padel": "Nexum Padel on Instagram",
    "Pedicel Marketing": "Pedicel Marketing",
    "Nexum Padel": "Nexum Padel",
    "Pista de pádel de la academia en Marbella, con palmeras al fondo":
        "The academy's padel court in Marbella, with palm trees behind",
    "Riki Padrón, Head Coach de la academia": "Riki Padrón, Head Coach at the academy",
    "Juampi Vanella, Head Coach de la academia": "Juampi Vanella, Head Coach at the academy",
    "Sesión de entrenamiento en pista": "A training session on court",
    "Jugador ejecutando un golpe durante un entrenamiento":
        "A player striking the ball during training",
    "Pistas de pádel de la academia en Marbella, con La Concha al fondo":
        "The academy's padel courts in Marbella, with La Concha mountain behind",
    "Grupo entrenando con uno de los coaches de la academia":
        "A group training with one of the academy coaches",
    "Entrenamiento de grupo en pista": "Group training on court",
    "Vista aérea del complejo de pistas de pádel en Marbella":
        "Aerial view of the padel court complex in Marbella",
    "Sesión de coaching en pista": "A coaching session on court",
    "Equipo de entrenadores tras una sesión de formación":
        "The coaching team after a training session",
    "Evento y masterclass en el club": "An event and masterclass at the club",
    "Sesión de grupo organizada en pista": "An organised group session on court",
    "Avenida de palmeras en Marbella al atardecer":
        "A palm-lined avenue in Marbella at sunset",
    "Jugadores entrenando durante un camp en Marbella":
        "Players training during a camp in Marbella",
    "Trabajo técnico durante una sesión de entrenamiento":
        "Technical work during a training session",
    # meta descriptions
    "Academia de pádel en Marbella. Entrenamiento para todos los niveles, desde quien empieza "
    "hasta quien compite, y programas para clubes.":
        "Padel academy in Marbella. Coaching for every level, from beginners to competitors, plus "
        "programmes for clubs.",
    "Academia de pádel en Marbella para todos los niveles.":
        "Padel academy in Marbella for every level.",
    "Programas intensivos de hasta 7 días para clubes de pádel en todo el mundo. Innovación, "
    "conocimiento y método para sus jugadores y técnicos.":
        "Intensive programmes of up to 7 days for padel clubs worldwide. Innovation, knowledge and "
        "method for their players and coaching staff.",
    "Camps de pádel en Marbella. Entrena en el Mediterráneo con programas a medida para tu nivel y "
    "disfruta de la Costa del Sol.":
        "Padel camps in Marbella. Train on the Mediterranean with programmes built for your level "
        "and enjoy the Costa del Sol.",
    "Solicita información sobre entrenamiento de pádel en Marbella o programas internacionales "
    "para jugadores y clubes.":
        "Request information about padel training in Marbella or international programmes for "
        "players and clubs.",
}
ATTR.update({k: v for k, v in TEXT.items()})

TAG_RE = re.compile(r"<[^>]*>", re.S)
ATTR_RE = re.compile(r'\b(' + "|".join(TRANSLATED_ATTRS) + r')="([^"]*)"')


def translate_tag(tag: str, es_route: str) -> str:
    """Translate prose attributes and repoint relative paths for the /en/ depth."""
    if tag.startswith("<!--"):
        return tag

    def attr(m: re.Match) -> str:
        name, value = m.group(1), m.group(2)
        return f'{name}="{ATTR.get(value.strip(), value)}"'

    tag = ATTR_RE.sub(attr, tag)

    # Shared resources live one level up from /en/.
    tag = re.sub(r'(?<=")(assets/|css/|js/)', r"../\1", tag)
    tag = re.sub(r'(?<=, )(assets/)', r"../\1", tag)   # extra srcset entries

    # Internal page links point at the English siblings.
    for es, en in ROUTES.items():
        tag = tag.replace(f'href="{es}"', f'href="{en}"')
    return tag


def build_page(es_route: str) -> str:
    src = (ROOT / es_route).read_text(encoding="utf-8")
    if '>"' in src:
        sys.exit(f"FATAL: {es_route} has '>' inside an attribute — the tag splitter "
                 "assumes it does not")

    parts, out = TAG_RE.split(src), []
    tags = TAG_RE.findall(src)
    for i, chunk in enumerate(parts):
        stripped = chunk.strip()
        if stripped:
            out.append(chunk.replace(stripped, TEXT.get(stripped, stripped), 1))
        else:
            out.append(chunk)
        if i < len(tags):
            out.append(translate_tag(tags[i], es_route))
    html = "".join(out)

    html = html.replace('<html lang="es">', '<html lang="en">', 1)

    en_route = ROUTES[es_route]
    alternates = (
        f'<link rel="alternate" hreflang="es" href="{SITE_URL}/{es_route}" />\n'
        f'<link rel="alternate" hreflang="en" href="{SITE_URL}/en/{en_route}" />\n'
        f'<link rel="alternate" hreflang="x-default" href="{SITE_URL}/{es_route}" />\n')
    html = html.replace('<link rel="stylesheet"', alternates + '<link rel="stylesheet"', 1)

    html = add_switcher(html, to_lang="es", href=f"../{es_route}")
    return html


# Flags are drawn inline rather than set as emoji: 🇪🇸/🇬🇧 render as the bare
# letters "ES"/"GB" on Windows, which would sit next to the real label and read
# as a typo. An outer <svg> clips to its own viewBox by default, so the Union
# Jack's diagonals need no clip path.
FLAGS = {
    "es": ('<svg class="flag" viewBox="0 0 24 16" aria-hidden="true" focusable="false">'
           '<rect width="24" height="16" fill="#AA151B"/>'
           '<rect y="4" width="24" height="8" fill="#F1BF00"/>'
           '</svg>'),
    "en": ('<svg class="flag" viewBox="0 0 24 16" aria-hidden="true" focusable="false">'
           '<rect width="24" height="16" fill="#012169"/>'
           '<path d="M0 0 24 16M24 0 0 16" stroke="#FFF" stroke-width="3.2"/>'
           '<path d="M0 0 24 16M24 0 0 16" stroke="#C8102E" stroke-width="1.7"/>'
           '<path d="M12 0v16M0 8h24" stroke="#FFF" stroke-width="5.4"/>'
           '<path d="M12 0v16M0 8h24" stroke="#C8102E" stroke-width="3.2"/>'
           '</svg>'),
}


def add_switcher(html: str, to_lang: str, href: str) -> str:
    """Append the other language as the last item in the primary nav."""
    label = "ES" if to_lang == "es" else "EN"
    # The flag is decorative; lang/hreflang already tell assistive tech and
    # crawlers what the link leads to, and the visible label repeats it.
    link = (f'\n      <a class="nav-link nav-lang" href="{href}" hreflang="{to_lang}" '
            f'lang="{to_lang}">{FLAGS[to_lang]}<span>{label}</span></a>')
    marker = "\n    </nav>"
    if marker not in html:
        sys.exit("FATAL: primary nav close tag not found")
    if 'class="nav-link nav-lang"' in html:
        html = re.sub(r'\n\s*<a class="nav-link nav-lang".*?</a>', "", html, flags=re.S)
    return html.replace(marker, link + marker, 1)


def build() -> None:
    EN.mkdir(parents=True, exist_ok=True)
    for es_route, en_route in ROUTES.items():
        (EN / en_route).write_text(build_page(es_route), encoding="utf-8")
        print(f"  {es_route:16} -> en/{en_route}")

    # The Spanish pages gain the reciprocal EN link and the same hreflang set.
    for es_route, en_route in ROUTES.items():
        page = ROOT / es_route
        html = original = page.read_text(encoding="utf-8")
        html = add_switcher(html, to_lang="en", href=f"en/{en_route}")
        if 'hreflang="x-default"' not in html:
            alternates = (
                f'<link rel="alternate" hreflang="es" href="{SITE_URL}/{es_route}" />\n'
                f'<link rel="alternate" hreflang="en" href="{SITE_URL}/en/{en_route}" />\n'
                f'<link rel="alternate" hreflang="x-default" href="{SITE_URL}/{es_route}" />\n')
            html = html.replace('<link rel="stylesheet"', alternates + '<link rel="stylesheet"', 1)
        if html != original:
            page.write_text(html, encoding="utf-8")
    print("  Spanish pages: EN switcher + hreflang added")


def check() -> int:
    """Fail if any Spanish string survived into the English build."""
    spanish = {s for s in TEXT if TEXT[s] != s} | {s for s in ATTR if ATTR[s] != s}
    problems = 0
    for es_route, en_route in ROUTES.items():
        page = EN / en_route
        if not page.exists():
            print(f"  en/{en_route:14} MISSING — run --build")
            problems += 1
            continue
        html = page.read_text(encoding="utf-8")
        # Developer comments stay in Spanish on purpose — they document the
        # generator and are never rendered. Only visitor-visible text counts.
        rendered = re.sub(r"<!--.*?-->", "", html, flags=re.S)
        leftovers = sorted({s for s in spanish if s in rendered}, key=len, reverse=True)
        broken = [p for p in re.findall(r'(?:src|href)="(\.\./[^"]+)"', html)
                  if not (EN / p).resolve().exists()]
        status = "ok" if not (leftovers or broken) else "FAIL"
        print(f"  en/{en_route:14} {status}  "
              f"{len(leftovers)} untranslated, {len(broken)} broken path(s)")
        for s in leftovers[:5]:
            print(f"      untranslated: {s[:88]}")
        for p in broken[:5]:
            print(f"      broken path : {p}")
        problems += len(leftovers) + len(broken)

    print(f"\n{'FAIL' if problems else 'OK'}: {problems} problem(s).")
    return 1 if problems else 0


def main() -> int:
    global ROOT, EN
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default="site-v2",
                    help="tree to operate on, relative to the project (default site-v2)")
    ap.add_argument("--build", action="store_true")
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()
    if not (args.build or args.check):
        ap.error("nothing to do — pass --build or --check")

    ROOT = PROJECT / args.root
    EN = ROOT / "en"
    if not (ROOT / "index.html").exists():
        sys.exit(f"FATAL: {ROOT}/index.html missing")
    if args.build:
        build()
    return check() if args.check else 0


if __name__ == "__main__":
    raise SystemExit(main())
