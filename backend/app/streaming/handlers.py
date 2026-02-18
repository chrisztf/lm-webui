from .event_system import EventHandler, StreamingEvent, EventType

class TokenHandler(EventHandler):
    def can_handle(self, event: StreamingEvent) -> bool:
        return event.type in [EventType.TEXT_CHUNK, EventType.TEXT_COMPLETE]

    async def handle(self, event: StreamingEvent) -> None:
        pass

class SearchHandler(EventHandler):
    def can_handle(self, event: StreamingEvent) -> bool:
        return event.type in [EventType.SEARCH_START, EventType.SEARCH_RESULT, EventType.SEARCH_END]

    async def handle(self, event: StreamingEvent) -> None:
        pass

class CodeHandler(EventHandler):
    def can_handle(self, event: StreamingEvent) -> bool:
        return event.type in [EventType.CODE_EXECUTION, EventType.CODE_RESULT]

    async def handle(self, event: StreamingEvent) -> None:
        pass

class ErrorHandler(EventHandler):
    def can_handle(self, event: StreamingEvent) -> bool:
        return event.type == EventType.ERROR

    async def handle(self, event: StreamingEvent) -> None:
        pass
