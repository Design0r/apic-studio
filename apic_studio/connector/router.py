from apic_studio.connector import c4d
from apic_studio.messaging import MessageRouter

msg_router = MessageRouter()
msg_router.include_router(c4d.core_router)
msg_router.include_router(c4d.models_router)
