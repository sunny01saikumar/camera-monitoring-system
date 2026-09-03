import threading
import time

class ServiceState:
    INSTALLED = "INSTALLED"
    RESOLVED = "RESOLVED"
    STARTING = "STARTING"
    ACTIVE = "ACTIVE"
    STOPPING = "STOPPING"
    UNINSTALLED = "UNINSTALLED"

class EventBus:
    """
    OSGi Event Admin Service.
    Enables asynchronous, decoupled event publishing/subscribing between bundles.
    """
    def __init__(self):
        self._listeners = {}
        self._lock = threading.Lock()

    def subscribe(self, topic, callback):
        with self._lock:
            if topic not in self._listeners:
                self._listeners[topic] = []
            if callback not in self._listeners[topic]:
                self._listeners[topic].append(callback)

    def unsubscribe(self, topic, callback):
        with self._lock:
            if topic in self._listeners and callback in self._listeners[topic]:
                self._listeners[topic].remove(callback)

    def publish(self, topic, event_data):
        with self._lock:
            callbacks = list(self._listeners.get(topic, []))
            
        for cb in callbacks:
            threading.Thread(target=self._safe_dispatch, args=(cb, event_data), daemon=True).start()

    def _safe_dispatch(self, callback, data):
        try:
            callback(data)
        except Exception as e:
            print(f"[OSGi EventBus Error] Subscriber failed: {e}")

class OSGiFramework:
    """
    OSGi-compliant Service Framework in Python.
    Provides dynamic service lifecycle management (INSTALLED, RESOLVED, ACTIVE),
    on-demand service execution, dependency injection, and event administration.
    """
    def __init__(self):
        self.event_bus = EventBus()
        self._services = {}
        self._states = {}
        self._lock = threading.Lock()

    def register_service(self, service_id, service_instance):
        """Registers a service bundle into the OSGi registry."""
        with self._lock:
            self._services[service_id] = service_instance
            self._states[service_id] = ServiceState.RESOLVED
            print(f"[OSGi Framework] Registered bundle service: '{service_id}' [RESOLVED]")

    def start_service(self, service_id):
        """Executes/Starts a registered service on-demand."""
        with self._lock:
            service = self._services.get(service_id)
            if not service:
                print(f"[OSGi Framework] Service '{service_id}' not found.")
                return False
                
            if self._states.get(service_id) == ServiceState.ACTIVE:
                return True # Already executing

            self._states[service_id] = ServiceState.STARTING

        try:
            if hasattr(service, "start"):
                service.start()
            with self._lock:
                self._states[service_id] = ServiceState.ACTIVE
            print(f"[OSGi Framework] Executing service: '{service_id}' [ACTIVE]")
            return True
        except Exception as e:
            with self._lock:
                self._states[service_id] = ServiceState.RESOLVED
            print(f"[OSGi Framework] Error starting service '{service_id}': {e}")
            return False

    def stop_service(self, service_id):
        """Stops/Pauses an executing service to conserve system CPU/memory."""
        with self._lock:
            service = self._services.get(service_id)
            if not service:
                return False
                
            if self._states.get(service_id) != ServiceState.ACTIVE:
                return True

            self._states[service_id] = ServiceState.STOPPING

        try:
            if hasattr(service, "stop"):
                service.stop()
            with self._lock:
                self._states[service_id] = ServiceState.RESOLVED
            print(f"[OSGi Framework] Deactivated service: '{service_id}' [RESOLVED]")
            return True
        except Exception as e:
            print(f"[OSGi Framework] Error stopping service '{service_id}': {e}")
            return False

    def get_service(self, service_id):
        """Retrieves a registered service instance."""
        with self._lock:
            return self._services.get(service_id)

    def get_service_states(self):
        """Returns the state of all registered services."""
        with self._lock:
            return {s_id: self._states[s_id] for s_id in self._services}

# Global OSGi framework instance
framework = OSGiFramework()
