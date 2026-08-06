"""Sampling for a plain IR LED and phototransistor break beam."""
import time


class IRBeam:
    def __init__(self, emitter, receiver, seen_value=0, settle_ms=5,
                 sample_count=5, sample_gap_us=200):
        if sample_count < 1 or sample_count % 2 == 0:
            raise ValueError("sample_count must be a positive odd number")
        self._emitter = emitter
        if len(receiver) > 1:
            self._receivers = receiver
        else:
            self._receivers = [receiver]
        self._seen_value = seen_value
        self._settle_ms = settle_ms
        self._sample_count = sample_count
        self._sample_gap_us = sample_gap_us
        self._emitter.value(0)

    def seen(self):
        seens = [ self.receiver_seen(r) for r in self._receivers]
        return all(seens)

    def receiver_seen(self, receiver):
        """Return a majority-voted sample, always leaving the emitter off."""
        matching = 0
        self._emitter.value(1)
        try:
            time.sleep_ms(self._settle_ms)
            for index in range(self._sample_count):
                if receiver.value() == self._seen_value:
                    matching += 1
                if index + 1 < self._sample_count:
                    time.sleep_us(self._sample_gap_us)
        finally:
            self._emitter.value(0)
        return matching > self._sample_count // 2

    def stop(self):
        """Switch the emitter off."""
        self._emitter.value(0)

