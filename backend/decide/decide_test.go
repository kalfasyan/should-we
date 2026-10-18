package decide

import "testing"

func TestFeaturesDropsBlanksAndDuplicates(t *testing.T) {
	got, err := Features([]string{" Price ", "", "price", "Commute time"})
	if err != nil {
		t.Fatal(err)
	}
	want := []Feature{{"price", "Price"}, {"commute_time", "Commute time"}}
	if len(got) != len(want) || got[0] != want[0] || got[1] != want[1] {
		t.Fatalf("got %v, want %v", got, want)
	}
	if _, err := Features([]string{"  ", "!!"}); err == nil {
		t.Fatal("expected an error for no usable labels")
	}
}

func TestCleanScoresRejectsOutOfRange(t *testing.T) {
	f := []Feature{{"price", "Price"}}
	for _, bad := range []float64{-1, 5.5, 2.3} {
		if _, err := CleanScores(f, Scores{"price": bad}); err == nil {
			t.Errorf("score %v should be rejected", bad)
		}
	}
	got, err := CleanScores(f, Scores{"price": 4.5, "unknown": 1})
	if err != nil || len(got) != 1 || got["price"] != 4.5 {
		t.Fatalf("got %v, %v", got, err)
	}
}

// The worked example from the v1 README: Alice 2.333, Bob 4.000, combined 3.17.
func TestRankMatchesReadmeExample(t *testing.T) {
	f := []Feature{{"price", "Price"}, {"color", "Color"}, {"eco", "Eco"}}
	people := []Person{
		{ID: "alice", Weights: Weights{"price": 3, "color": 5, "eco": 1},
			Ratings: map[string]Scores{"car": {"price": 3, "color": 2, "eco": 2}}},
		{ID: "bob", Weights: Weights{"price": 5, "color": 3, "eco": 5},
			Ratings: map[string]Scores{"car": {"price": 4, "color": 4, "eco": 4}}},
	}
	got := Rank(f, people, []Option{{ID: "car"}})
	if got[0].Score != 3.17 || got[0].RatedBy != 2 {
		t.Fatalf("got %+v", got[0])
	}
	if got[0].ByPerson[0].Score != 2.33 || got[0].ByPerson[1].Score != 4 {
		t.Fatalf("by person %+v", got[0].ByPerson)
	}
	if got[0].Split {
		t.Fatal("2.33 vs 4 is not split")
	}
}

func TestRankOrdersBestFirstAndUnratedLast(t *testing.T) {
	f := []Feature{{"price", "Price"}}
	people := []Person{
		{ID: "a", Weights: Weights{"price": 3}, Ratings: map[string]Scores{
			"low": {"price": 1}, "high": {"price": 5}}},
		{ID: "b", Weights: Weights{"price": 3}, Ratings: map[string]Scores{
			"low": {"price": 5}}},
	}
	got := Rank(f, people, []Option{{ID: "none"}, {ID: "low"}, {ID: "high"}})
	if got[0].Option != "high" || got[1].Option != "low" || got[2].Option != "none" {
		t.Fatalf("order %v %v %v", got[0].Option, got[1].Option, got[2].Option)
	}
	if !got[1].Split {
		t.Fatal("1 vs 5 should be split")
	}
	if got[2].RatedBy != 0 || got[2].Score != 0 {
		t.Fatalf("unrated %+v", got[2])
	}
}

func TestPersonScoreIgnoresDontCareAndUsesDefaults(t *testing.T) {
	f := []Feature{{"price", "Price"}, {"size", "Size"}}
	// price doesn't matter at all, so only size counts
	if s, ok := PersonScore(f, Weights{"price": 0, "size": 5}, Scores{"price": 0, "size": 4}); !ok || s != 4 {
		t.Fatalf("got %v %v", s, ok)
	}
	if _, ok := PersonScore(f, Weights{"price": 0, "size": 0}, Scores{"price": 3}); ok {
		t.Fatal("all-zero weights should not count")
	}
	// no weights saved yet means Important for every point
	if s, ok := PersonScore(f, nil, Scores{"price": 2, "size": 4}); !ok || s != 3 {
		t.Fatalf("got %v %v", s, ok)
	}
}
