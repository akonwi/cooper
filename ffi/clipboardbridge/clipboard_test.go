package clipboardbridge

import "testing"

func TestCancelIsIdempotent(t *testing.T) {
	backend := New(nil)
	backend.Cancel()
	backend.Cancel()

	select {
	case <-backend.ctx.Done():
	default:
		t.Fatal("clipboard lifetime context was not cancelled")
	}
}

func TestSuspendAndResumeRotateReadLifetime(t *testing.T) {
	backend := New(nil)
	initial := backend.ctx
	backend.Suspend()
	select {
	case <-initial.Done():
	default:
		t.Fatal("suspended clipboard lifetime was not cancelled")
	}

	backend.Resume()
	if backend.ctx == initial {
		t.Fatal("clipboard resume did not create a fresh lifetime")
	}
	select {
	case <-backend.ctx.Done():
		t.Fatal("resumed clipboard lifetime is already cancelled")
	default:
	}

	backend.Cancel()
}
