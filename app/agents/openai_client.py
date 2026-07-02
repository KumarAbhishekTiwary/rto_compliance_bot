"""OpenAI client configured for corporate proxy + SSL. Must be imported first."""
import os
import sys
import ssl
import httpx
from dotenv import load_dotenv

if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

load_dotenv()

try:
    from openai import AsyncOpenAI
    from agents import set_default_openai_client, set_tracing_disabled

    set_tracing_disabled(True)

    DISABLE_SSL = os.getenv("DISABLE_SSL_VERIFY", "false").lower() == "true"
    CA_BUNDLE = os.getenv("REQUESTS_CA_BUNDLE") or os.getenv("SSL_CERT_FILE")
    PROXY = os.getenv("HTTPS_PROXY") or None

    if CA_BUNDLE and os.path.exists(CA_BUNDLE):
        verify_setting = ssl.create_default_context(cafile=CA_BUNDLE)
        print(f"✅ Using corporate CA bundle: {CA_BUNDLE}")
    elif DISABLE_SSL:
        verify_setting = False
        import urllib3
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        print("⚠️  SSL verification DISABLED (dev mode)")
    else:
        verify_setting = True

    http_client = httpx.AsyncClient(
        verify=verify_setting,
        timeout=60.0,
        proxy=PROXY,
    )

    custom_openai = AsyncOpenAI(
        api_key=os.getenv("OPENAI_API_KEY"),
        http_client=http_client,
    )
    set_default_openai_client(custom_openai)
    print(f"✅ OpenAI client configured (proxy: {PROXY or 'none'})")

except ImportError as e:
    print(f"⚠️  openai-agents not installed: {e}. Run: pip install openai-agents")
