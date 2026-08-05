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
import json
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
    "privacidad.html": "privacy.html",
}

# Attributes whose values are prose and must be translated. data-label-less is
# the collapsed-state label js/reviews.js swaps in, so it is visitor-visible too.
TRANSLATED_ATTRS = ("alt", "title", "aria-label", "content", "placeholder",
                    "data-label-less")

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
    # Footer, reorganised 2026-08-03: the tagline no longer repeats the location,
    # which now appears once under Contacto.
    "Academia de pádel para todos los niveles.": "Padel academy for every level.",
    "Navegación": "Navigation",
    "Pie de página": "Footer",
    "Política de Privacidad": "Privacy Policy",
    "EN": "EN",

    # --- privacy page -------------------------------------------------------
    "Privacidad | Nexum Padel": "Privacy | Nexum Padel",
    "Política de privacidad de Nexum Padel: qué datos tratamos, con qué finalidad y cómo "
    "ejercer tus derechos.":
        "Nexum Padel's privacy policy: what data we handle, why, and how to exercise your rights.",
    "Legal": "Legal",
    "Última actualización: 3 de agosto de 2026": "Last updated: 3 August 2026",
    "Esta web trata la mínima cantidad de datos posible. No usamos cookies, no hay analítica, "
    "no hay publicidad y no creamos perfiles de nadie.":
        "This site handles as little data as possible. We use no cookies, there is no analytics, "
        "no advertising, and we build no profiles of anyone.",
    "1. Quién es el responsable": "1. Who is responsible",
    "Titular:": "Legal entity:",
    "PENDIENTE — nombre o razón social": "PENDING — name or registered company name",
    "NIF:": "Tax ID (NIF):",
    "PENDIENTE": "PENDING",
    "Domicilio:": "Registered address:",
    "PENDIENTE — dirección fiscal": "PENDING — registered address",
    # Street and town stay as they are — only the country name is localised.
    "Av. de Barcelona, 8, 29670 San Pedro Alcántara, Málaga, España":
        "Av. de Barcelona, 8, 29670 San Pedro Alcántara, Málaga, Spain",
    "Email:": "Email:",
    "Web:": "Website:",
    "nexumpadel.es": "nexumpadel.es",
    "2. Qué datos tratamos y para qué": "2. What data we handle, and why",
    "Solo tratamos los datos que nos envías tú por tu propia iniciativa cuando nos escribes: tu "
    "nombre, tu dirección de correo y lo que nos cuentes en el mensaje. Los usamos únicamente "
    "para responderte y, si procede, prepararte una propuesta.":
        "We only handle what you send us yourself when you write to us: your name, your email "
        "address and whatever you tell us in the message. We use it solely to reply and, where "
        "relevant, to put a proposal together for you.",
    "El formulario de contacto de esta web no envía nada por sí solo: abre tu propio programa de "
    "correo con el mensaje ya escrito, y eres tú quien decide enviarlo. Es decir, tus datos "
    "llegan a nuestro buzón como un email normal y corriente, y esta web no los guarda en ningún "
    "momento.":
        "The contact form on this site sends nothing by itself: it opens your own mail app with "
        "the message pre-written, and you decide whether to send it. Your details reach our inbox "
        "as an ordinary email, and this website never stores them at any point.",
    "3. Con qué legitimación": "3. Legal basis",
    "Tu consentimiento, que das al escribirnos voluntariamente (RGPD art. 6.1.a), y la aplicación "
    "de medidas precontractuales cuando nos pides información sobre un programa o una reserva "
    "(RGPD art. 6.1.b).":
        "Your consent, given when you choose to write to us (GDPR art. 6.1.a), and pre-contractual "
        "steps when you ask about a programme or a booking (GDPR art. 6.1.b).",
    "4. Cuánto tiempo los conservamos": "4. How long we keep it",
    "Conservamos tu correo el tiempo necesario para atender tu consulta y, si acabas siendo "
    "cliente, durante los plazos que exige la normativa fiscal y mercantil. Si no llegamos a "
    "tener relación, borramos la conversación cuando deja de tener sentido mantenerla.":
        "We keep your email for as long as it takes to deal with your enquiry and, if you become "
        "a client, for the periods tax and commercial law require. If nothing comes of it, we "
        "delete the exchange once there is no reason to keep it.",
    "5. Quién más puede ver tus datos": "5. Who else can see your data",
    "No vendemos ni cedemos tus datos a nadie. Solo intervienen los proveedores que hacen falta "
    "para que la web y el correo funcionen:":
        "We do not sell or hand your data to anyone. The only third parties involved are the "
        "providers needed to run the website and the mailbox:",
    "Alojamiento web:": "Web hosting:",
    "servidor propio en Scaleway (Francia, Unión Europea).":
        "our own server at Scaleway (France, European Union).",
    "Correo electrónico:": "Email:",
    "Hostinger, proveedor del buzón info@nexumpadel.es.":
        "Hostinger, provider of the info@nexumpadel.es mailbox.",
    "Google Fonts:": "Google Fonts:",
    "las tipografías de la web se cargan desde servidores de Google, lo que implica que tu "
    "dirección IP les es comunicada al abrir la página. No se instala ninguna cookie por este "
    "motivo.":
        "the site's typefaces load from Google's servers, which means your IP address is disclosed "
        "to them when the page opens. No cookie is set as a result.",
    "6. Cookies": "6. Cookies",
    "Esta web no instala cookies, ni propias ni de terceros, y tampoco usa almacenamiento local "
    "del navegador. No hay Google Analytics, ni píxeles de redes sociales, ni herramientas de "
    "seguimiento de ningún tipo. Por eso no verás ningún aviso de cookies: sencillamente no hay "
    "nada que consentir.":
        "This site sets no cookies, neither its own nor third-party, and uses no browser local "
        "storage. There is no Google Analytics, no social media pixels and no tracking tools of "
        "any kind. That is why you will see no cookie banner: there is simply nothing to consent "
        "to.",
    "7. Enlaces a otras webs": "7. Links to other sites",
    "Desde aquí enlazamos a perfiles y páginas de terceros, como nuestro Instagram. Cuando sales "
    "de esta web, la política de privacidad que se te aplica es la de ese sitio, no la nuestra.":
        "We link out to third-party pages and profiles, such as our Instagram. Once you leave this "
        "site, the privacy policy that applies to you is theirs, not ours.",
    "8. Tus derechos": "8. Your rights",
    "Puedes pedirnos en cualquier momento acceder a tus datos, rectificarlos, suprimirlos, "
    "oponerte al tratamiento, limitarlo o solicitar su portabilidad. Basta con escribirnos a":
        "You may ask us at any time to access your data, correct it, delete it, object to or "
        "restrict its processing, or request its portability. Just write to",
    "indicando qué derecho quieres ejercer.": "telling us which right you wish to exercise.",
    "Si consideras que no hemos atendido bien tu solicitud, puedes reclamar ante la Agencia "
    "Española de Protección de Datos (":
        "If you feel we have not handled your request properly, you may complain to the Spanish "
        "Data Protection Agency (",
    "aepd.es": "aepd.es",
    "9. Seguridad": "9. Security",
    "La web se sirve íntegramente por conexión cifrada (HTTPS). Aun así, ningún sistema es "
    "infalible: te recomendamos no enviarnos por correo información sensible que no sea necesaria "
    "para lo que nos pides.":
        "The whole site is served over an encrypted connection (HTTPS). Even so, no system is "
        "infallible: we recommend not emailing us sensitive information beyond what your request "
        "actually needs.",
    "10. Cambios en esta política": "10. Changes to this policy",
    "Si cambiamos la forma de tratar los datos —por ejemplo, si algún día añadimos un formulario "
    "que sí guarde la información o alguna herramienta de medición— actualizaremos esta página y "
    "la fecha que aparece arriba.":
        "If we change how we handle data — say we one day add a form that does store what you "
        "type, or any measurement tool — we will update this page and the date shown above.",
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
    "Club de playa en Marbella con una pista de pádel sobre la arena y el mar al fondo":
        "A beach club in Marbella with a padel court on the sand and the sea behind",
    "Pista de pádel de la academia en Marbella, con palmeras al fondo":
        "The academy's padel court in Marbella, with palm trees behind",
    "Riki Padrón, Head Coach de la academia": "Riki Padrón, Head Coach at the academy",
    "Juampi Vanella, Head Coach de la academia": "Juampi Vanella, Head Coach at the academy",
    "Sesión de entrenamiento en pista": "A training session on court",
    "Jugador ejecutando un golpe durante un entrenamiento":
        "A player striking the ball during training",
    "Pistas de pádel de la academia en Marbella, con La Concha al fondo":
        "The academy's padel courts in Marbella, with La Concha mountain behind",
    "Pistas de pádel en Marbella con La Concha al fondo":
        "Padel courts in Marbella with La Concha mountain behind",
    "Pista de pádel del club bajo un cielo despejado en Marbella":
        "The club's padel court under clear skies in Marbella",
    "Tres jugadores posando junto a la red de la pista":
        "Three players by the net on court",
    "Tres jugadores con sus palas al final de un entrenamiento":
        "Three players with their rackets at the end of a session",
    "Entrenamiento de grupo en pista": "Group training on court",
    "Vista aérea del complejo de pistas de pádel en Marbella":
        "Aerial view of the padel court complex in Marbella",
    "Sesión de coaching en pista": "A coaching session on court",
    "Equipo de entrenadores tras una sesión de formación":
        "The coaching team after a training session",
    "Evento y masterclass en el club": "An event and masterclass at the club",
    "Sesión de grupo organizada en pista": "An organised group session on court",
    "Sesión de consultoría con un club, con las pistas al fondo":
        "A consulting session with a club, courts visible behind",
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

def _load_review_translations() -> dict:
    """Spanish review text -> the client's original English wording.

    The reviews arrived in English and are rendered in Spanish on the ES pages,
    so /en/ must show the ORIGINAL words back, not a re-translation of a
    translation. Pulled from assets/reviews.json so the pair stays in one place;
    adding a review needs no edit here.
    """
    path = PROJECT / "site-v2" / "assets" / "reviews.json"
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    reviews = data.get("reviews") or []
    out = {}
    for r in reviews:
        out[r["text_es"]] = r["text_en"]

    if reviews:
        # Spain writes 4,7 and the UK writes 4.7. Derived from the ratings, not
        # hardcoded, so it stays correct when a review is added or changed.
        avg = sum(int(r["rating"]) for r in reviews) / len(reviews)
        es = f"{avg:.1f}".replace(".", ",")
        en = f"{avg:.1f}"
        out[es] = en
        out[f"{es} de 5 estrellas"] = f"{en} out of 5 stars"
        out[f"Ver las {len(reviews)} reseñas"] = f"See all {len(reviews)} reviews"
    return out


# Country labels used by the review cards, and the review-section chrome.
TEXT.update({
    "España": "Spain", "Noruega": "Norway", "Suecia": "Sweden",
    "Reino Unido": "United Kingdom", "Irlanda": "Ireland", "Alemania": "Germany",
    "Francia": "France", "Suiza": "Switzerland", "Marruecos": "Morocco",
    "Ver menos": "Show fewer",
    "Ver las 20 reseñas": "See all 20 reviews",
})
TEXT.update(_load_review_translations())

ATTR.update({k: v for k, v in TEXT.items()})
# Star aria-labels are generated per rating, so cover the range rather than
# listing whichever values happen to appear today.
ATTR.update({f"{n} de 5 estrellas": f"{n} out of 5 stars" for n in range(0, 6)})
ATTR["4,7 de 5 estrellas"] = "4.7 out of 5 stars"
ATTR["Ver menos"] = "Show fewer"

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


def untranslated_sources() -> dict[str, list[str]]:
    """Spanish strings on the ES pages that have no entry in TEXT/ATTR.

    This is the gate that actually matters. Checking only that *known* Spanish
    strings disappeared from /en/ proves nothing about strings nobody mapped:
    privacidad.html was added with zero entries and --check reported a single
    problem while the entire English page was still in Spanish.

    So instead of asking "did the strings I know about get translated?", ask
    "is there anything on the Spanish page I never gave a translation for?".
    """
    missing: dict[str, list[str]] = {}
    for es_route in ROUTES:
        page = ROOT / es_route
        if not page.exists():
            continue
        html = page.read_text(encoding="utf-8")
        html = re.sub(r"<!--.*?-->", "", html, flags=re.S)
        html = re.sub(r"<(script|style|svg)\b.*?</\1>", "", html, flags=re.S)
        # translate="no" is an explicit instruction that the content is not
        # copy — reviewer names, avatar initials. Nothing to define there.
        html = re.sub(r'<(\w+)[^>]*\btranslate="no"[^>]*>.*?</\1>', "", html, flags=re.S)

        found = []
        for chunk in TAG_RE.split(html):
            s = " ".join(chunk.split())
            # Skip anything with no letters: bare numerals like "01" and lone
            # punctuation need no translation and would only add noise.
            if s and any(c.isalpha() for c in s) and s not in TEXT:
                found.append(s)
        for tag in TAG_RE.findall(html):
            for name, value in ATTR_RE.findall(tag):
                v = value.strip()
                if v and any(c.isalpha() for c in v) and v not in ATTR:
                    found.append(f"@{name}={v}")
        if found:
            missing[es_route] = sorted(set(found), key=len, reverse=True)
    return missing


def check() -> int:
    """Fail if any Spanish string survived into the English build."""
    spanish = {s for s in TEXT if TEXT[s] != s} | {s for s in ATTR if ATTR[s] != s}
    problems = 0

    gaps = untranslated_sources()
    for route, items in gaps.items():
        print(f"  {route:16} {len(items)} string(s) with NO translation defined")
        for s in items[:6]:
            print(f"      missing: {s[:96]}")
        problems += len(items)
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
