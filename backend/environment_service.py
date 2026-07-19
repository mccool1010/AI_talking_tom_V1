class EnvironmentService:

    def __init__(self):

        self.person_present = False
        self.people_count = 0

        # Objects currently confirmed visible
        self.objects = []

        # Objects that just appeared (debounced)
        self.new_objects = []

        # Objects that just disappeared (debounced)
        self.removed_objects = []

        self.brightness = "normal"

        self.user_left = False
        self.user_returned = False

        # Debounce tracking: count consecutive frames an object is seen/missing
        self._pending_new = {}      # object -> consecutive frames seen
        self._pending_removed = {}  # object -> consecutive frames missing
        self._debounce_threshold = 3  # require 3 consecutive frames

    def get_environment(self):
        return {
            "person_present": self.person_present,
            "people_count": self.people_count,
            "objects": self.objects,
            "new_objects": self.new_objects,
            "removed_objects": self.removed_objects,
            "brightness": self.brightness,
            "user_left": self.user_left,
            "user_returned": self.user_returned
        }

    def update_person(self, detected, people_count):

        self.people_count = people_count

        self.user_left = False
        self.user_returned = False

        # Debounce: require consistent detection for 3 frames
        if detected != self.person_present:
            self._person_change_count = getattr(self, '_person_change_count', 0) + 1
            if self._person_change_count >= self._debounce_threshold:
                previous = self.person_present
                self.person_present = detected
                self._person_change_count = 0

                if previous and not detected:
                    self.user_left = True
                elif not previous and detected:
                    self.user_returned = True
        else:
            self._person_change_count = 0

    def update_objects(self, detected_objects):

        previous = set(self.objects)
        current = set(detected_objects)

        raw_new = current - previous
        raw_removed = previous - current

        # --- Debounce new objects ---
        confirmed_new = []
        for obj in raw_new:
            self._pending_new[obj] = self._pending_new.get(obj, 0) + 1
            if self._pending_new[obj] >= self._debounce_threshold:
                confirmed_new.append(obj)
                del self._pending_new[obj]

        # Reset counters for objects no longer candidates
        for obj in list(self._pending_new.keys()):
            if obj not in raw_new:
                del self._pending_new[obj]

        # --- Debounce removed objects ---
        confirmed_removed = []
        for obj in raw_removed:
            self._pending_removed[obj] = self._pending_removed.get(obj, 0) + 1
            if self._pending_removed[obj] >= self._debounce_threshold:
                confirmed_removed.append(obj)
                del self._pending_removed[obj]

        # Reset counters for objects that reappeared
        for obj in list(self._pending_removed.keys()):
            if obj not in raw_removed:
                del self._pending_removed[obj]

        self.new_objects = confirmed_new
        self.removed_objects = confirmed_removed

        # Only update confirmed objects list when debounced
        if confirmed_new or confirmed_removed:
            self.objects = list(current)