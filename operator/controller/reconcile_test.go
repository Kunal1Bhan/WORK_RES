package controller

import (
	"testing"

	"github.com/kunal1bhan/work-res/operator/api/v1alpha1"
)

func svc() v1alpha1.ProductionService {
	return v1alpha1.ProductionService{
		Name:   "lab-api",
		Spec:   v1alpha1.ProductionServiceSpec{Image: "lab-api:v2", Replicas: 2, RollbackOnError: true},
		Status: v1alpha1.ProductionServiceStatus{ReadyImage: "lab-api:v1"},
	}
}

func TestImageDrift(t *testing.T) {
	acts, st := Reconcile(svc(), Actual{Replicas: 2, AvailableReplicas: 2, Image: "lab-api:v1"})
	if len(acts) != 1 || acts[0].Kind != "set-image" || acts[0].Image != "lab-api:v2" {
		t.Fatalf("expected set-image to v2, got %+v", acts)
	}
	if st.Phase != "Progressing" {
		t.Fatalf("expected Progressing, got %s", st.Phase)
	}
}

func TestReplicaDriftScales(t *testing.T) {
	s := svc()
	s.Spec.RollbackOnError = false
	acts, st := Reconcile(s, Actual{Replicas: 1, AvailableReplicas: 1, Image: "lab-api:v2"})
	if len(acts) != 1 || acts[0].Kind != "scale" || acts[0].Replica != 2 {
		t.Fatalf("expected scale to 2, got %+v", acts)
	}
	if st.Phase != "Progressing" {
		t.Fatalf("expected Progressing, got %s", st.Phase)
	}
}

func TestFailedRolloutRollsBack(t *testing.T) {
	acts, st := Reconcile(svc(), Actual{Replicas: 2, AvailableReplicas: 0, Image: "lab-api:v2"})
	if len(acts) != 1 || acts[0].Kind != "rollback" || acts[0].Image != "lab-api:v1" {
		t.Fatalf("expected rollback to v1, got %+v", acts)
	}
	if st.Phase != "Failed" {
		t.Fatalf("expected Failed, got %s", st.Phase)
	}
}

func TestSteadyStateReady(t *testing.T) {
	acts, st := Reconcile(svc(), Actual{Replicas: 2, AvailableReplicas: 2, Image: "lab-api:v2"})
	if len(acts) != 0 {
		t.Fatalf("expected no actions, got %+v", acts)
	}
	if st.Phase != "Ready" || st.ReadyImage != "lab-api:v2" {
		t.Fatalf("expected Ready/v2, got %+v", st)
	}
}

func TestNoFlapWhenAlreadyRolledBack(t *testing.T) {
	s := svc()
	s.Status.Phase = "Failed" // rollback to v1 already recorded
	acts, st := Reconcile(s, Actual{Replicas: 2, AvailableReplicas: 2, Image: "lab-api:v1"})
	if len(acts) != 0 || st.Phase != "Failed" {
		t.Fatalf("expected no flap, got %+v/%s", acts, st.Phase)
	}
}
