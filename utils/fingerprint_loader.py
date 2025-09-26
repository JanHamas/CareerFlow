from pathlib import Path
import json, random
import logging

# Logger
logger = logging.getLogger("spider")


BAISE_DIR = Path(__file__).resolve().parent
FINGERPRINTS_DIR = BAISE_DIR / "fingerprints"

# list of fingerprint 
fingerprints = []
seen_user_agent = set() # base on uniqe useragent saved fingerprint

# load and append all fingerprint to list
for path in FINGERPRINTS_DIR.glob("*.json"):
    try:
        with open(path, 'r', encoding = 'utf-8') as f:
            content = f.read().strip()
            
            if not content:
                logger.info(f"⚠ Skipped empty file: {path.name}")
                continue
        
            fingerprint = json.loads(content)
            user_agent = fingerprint.get("navigator", {}).get("userAgent", "").strip() 
            
            if not user_agent:
               logger.info(f"UserAgent not found {path.name}")  

            if user_agent not in seen_user_agent: 
                seen_user_agent.add(user_agent)
                fingerprints.append(fingerprint)
                # print(f"✔ loaded: {path.name} | UA {user_agent}")
            else:
                pass
                # print(f"🔁 Duplicate skipped: {path.name}")
    
    except json.JSONDecodeError as e:
        logger.error(f"❌ JSON error in {path.name}: {e}")
    except UnicodeDecodeError as e:
      logger.error(f"❌ Encoding error in {path.name}: {e}")
    except Exception as e:
      logger.error(f"❌ Unexpected error in {path.name}: {e}")
    
async def load_fingerprint(index=0):
    if index==0:
        logger.info(f"✔  Unique fingerprints loaded")

    fingerprint = fingerprints[index]

    # Safe dictionary extractions with fallbacks
    nav = fingerprint.get("navigator") or {}
    screen = fingerprint.get("screen") or {}
    battery = fingerprint.get("battery") or {}
    plugins_data = fingerprint.get("pluginsData") or {}
    plugins = plugins_data.get("plugins") or []
    fonts = fingerprint.get("fonts") or []
    audio_codecs = fingerprint.get("audioCodecs") or {}
    video_codecs = fingerprint.get("videoCodecs") or {}
    video_card = fingerprint.get("videoCard") or {}
    ua_data = nav.get("userAgentData") or {}

    # Set defaults for screen dimensions
    screen.setdefault("width", 1920)
    screen.setdefault("height", 1080)
    screen.setdefault("outerWidth", screen["width"])
    screen.setdefault("outerHeight", screen["height"])
    screen.setdefault("screenX", 0)
    screen.setdefault("devicePixelRatio", 1.0)

    plugin_objects = []
    for p in plugins:
        plugin_objects.append({
            "name": p.get("name", ""),
            "description": p.get("description", ""),
            "filename": p.get("filename", ""),
            "mimeTypes": [{
                "type": m.get("type", ""),
                "suffixes": m.get("suffixes", ""),
                "description": m.get("description", "")
            } for m in p.get("mimeTypes", [])]
        })

    # JS injection script (you can keep this as-is, just ensure safety when using .get)
    script = f"""
    Object.defineProperty(window, 'innerWidth', {{
        get: () => {screen['width']}
    }});
    Object.defineProperty(window, 'innerHeight', {{
        get: () => {screen['height']}
    }});
    Object.defineProperty(window, 'outerWidth', {{
        get: () => {screen['outerWidth']}
    }});
    Object.defineProperty(window, 'outerHeight', {{
        get: () => {screen['outerHeight']}
    }});
    Object.defineProperty(window, 'screenX', {{
        get: () => {screen['screenX']}
    }});
    Object.defineProperty(window, 'devicePixelRatio', {{
        get: () => {screen['devicePixelRatio']}
    }});

    const navigatorProps = {{
        userAgent: {json.dumps(nav.get('userAgent', ''))},
        language: {json.dumps(nav.get('language', 'en-US'))},
        languages: {json.dumps(nav.get('languages', ['en-US']))},
        platform: {json.dumps(nav.get('platform', ''))},
        deviceMemory: {nav.get('deviceMemory') or 8},
        hardwareConcurrency: {nav.get('hardwareConcurrency') or 4},
        maxTouchPoints: {nav.get('maxTouchPoints') or 0},
        product: {json.dumps(nav.get('product', 'Gecko'))},
        productSub: {json.dumps(nav.get('productSub', '20030107'))},
        vendor: {json.dumps(nav.get('vendor', 'Google Inc.'))},
        vendorSub: {json.dumps(nav.get('vendorSub', ''))},
        doNotTrack: {json.dumps(nav.get("doNotTrack", "unspecified"))}
    }};
    for (const [prop, value] of Object.entries(navigatorProps)) {{
        Object.defineProperty(navigator, prop, {{
            value: value,
            writable: false,
            configurable: false,
            enumerable: true
        }});
    }}

    const fontList = {json.dumps(fonts)};
    Object.defineProperty(document, 'fonts', {{
        value: {{
            status: 'loaded',
            ready: Promise.resolve(),
            check: () => true,
            load: () => Promise.resolve(),
            values: () => fontList.map(f => new FontFace(f, '')).values()
        }},
        configurable: false
    }});

    Object.defineProperty(navigator, 'getBattery', {{
        value: () => Promise.resolve({{
            charging: {json.dumps(battery.get('charging', True))},
            chargingTime: {json.dumps(battery.get('chargingTime', 0))},
            dischargingTime: {json.dumps(battery.get('dischargingTime', 0))},
            level: {battery.get('level', 1.0)}
        }}),
        configurable: false
    }});

    HTMLVideoElement.prototype.canPlayType = function(type) {{
        const codecs = {json.dumps(video_codecs)};
        const match = type.match(/video\\/(\\w+)/);
        if (match) {{
            const format = match[1];
            return codecs[format] || 'maybe';
        }}
        return 'maybe';
    }};

    HTMLAudioElement.prototype.canPlayType = function(type) {{
        const codecs = {json.dumps(audio_codecs)};
        const match = type.match(/audio\\/(\\w+)/);
        if (match) {{
            const format = match[1];
            return codecs[format] || 'maybe';
        }}
        return 'maybe';
    }};

    const OriginalImage = window.Image;
    window.Image = function() {{
        const img = new OriginalImage();
        img.addEventListener('error', () => {{
            Object.defineProperty(img, 'naturalWidth', {{ value: 16 }});
            Object.defineProperty(img, 'naturalHeight', {{ value: 16 }});
        }}, {{ once: true }});
        return img;
    }};

    const originalPermissionsQuery = navigator.permissions.query;
    navigator.permissions.query = async (descriptor) => {{
        if (descriptor.name === 'geolocation') {{
            return {{ state: 'denied' }};
        }}
        return await originalPermissionsQuery(descriptor);
    }};

    if (navigator.userAgentData) {{
        Object.defineProperty(navigator.userAgentData, 'brands', {{
            value: {json.dumps(ua_data.get('brands', []))},
            writable: false
        }});
        Object.defineProperty(navigator.userAgentData, 'mobile', {{
            value: {json.dumps(ua_data.get('mobile', False))},
            writable: false
        }});
        Object.defineProperty(navigator.userAgentData, 'platform', {{
            value: {json.dumps(ua_data.get('platform', ''))},
            writable: false
        }});
    }}

    const originalGetParameter = WebGLRenderingContext.prototype.getParameter;
    WebGLRenderingContext.prototype.getParameter = function(param) {{
        if (param === 37445) return {json.dumps(video_card.get("vendor", "Google Inc."))};
        if (param === 37446) return {json.dumps(video_card.get("renderer", "ANGLE (Google Inc.)"))};
        return originalGetParameter.call(this, param);
    }};
    """

    return script
