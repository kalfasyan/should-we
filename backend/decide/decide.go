// Package decide holds should-we's rules: what a valid decision, priority and
// rating look like, and how everyone's answers combine into one ranking.
package decide

import (
	"errors"
	"math"
	"regexp"
	"sort"
	"strings"
)

// Feature is one thing that matters when choosing, such as "Price".
type Feature struct {
	Key   string `json:"key"`
	Label string `json:"label"`
}

// Weights are how much each feature matters to one person, by feature key.
// The app offers Don't care (0), A little (1), Important (3) and Must-have (5).
type Weights map[string]int

// Scores are one person's ratings of one option, 0 (bad) to 5 (great).
type Scores map[string]float64

// Person is someone taking part, with their priorities and their ratings by option id.
type Person struct {
	ID      string            `json:"id"`
	Name    string            `json:"name"`
	Weights Weights           `json:"weights"`
	Ratings map[string]Scores `json:"ratings"`
}

// Option is one candidate, such as an apartment.
type Option struct {
	ID   string `json:"id"`
	Name string `json:"name"`
	Note string `json:"note"`
}

const (
	MaxFeatures   = 12
	DefaultWeight = 3
	// opinions count as split when people's scores for an option differ this much (std dev)
	SplitThreshold = 1.5
)

var nonKey = regexp.MustCompile(`[^a-z0-9]+`)

func keyOf(label string) string {
	return strings.Trim(nonKey.ReplaceAllString(strings.ToLower(label), "_"), "_")
}

// Features turns labels into features, dropping blanks and duplicates.
func Features(labels []string) ([]Feature, error) {
	var out []Feature
	seen := map[string]bool{}
	for _, l := range labels {
		l = strings.TrimSpace(l)
		k := keyOf(l)
		if k == "" || seen[k] {
			continue
		}
		if len([]rune(l)) > 60 {
			return nil, errors.New("keep each point under 60 characters")
		}
		seen[k] = true
		out = append(out, Feature{Key: k, Label: l})
	}
	if len(out) == 0 {
		return nil, errors.New("list at least one thing that matters")
	}
	if len(out) > MaxFeatures {
		return nil, errors.New("list at most 12 things that matter")
	}
	return out, nil
}

// DefaultWeights starts everyone at Important, so their ratings count straight away.
func DefaultWeights(features []Feature) Weights {
	w := Weights{}
	for _, f := range features {
		w[f.Key] = DefaultWeight
	}
	return w
}

// CleanWeights keeps only known features and checks every value is 0–5.
func CleanWeights(features []Feature, in Weights) (Weights, error) {
	out := Weights{}
	for _, f := range features {
		v, ok := in[f.Key]
		if !ok {
			continue
		}
		if v < 0 || v > 5 {
			return nil, errors.New("priorities go from 0 to 5")
		}
		out[f.Key] = v
	}
	return out, nil
}

// CleanScores keeps only known features and checks every score is 0–5 in half steps.
func CleanScores(features []Feature, in Scores) (Scores, error) {
	out := Scores{}
	for _, f := range features {
		v, ok := in[f.Key]
		if !ok {
			continue
		}
		if v < 0 || v > 5 || math.Mod(v*2, 1) != 0 {
			return nil, errors.New("ratings go from 0 to 5 in half steps")
		}
		out[f.Key] = v
	}
	if len(out) == 0 {
		return nil, errors.New("rate at least one point")
	}
	return out, nil
}

// PersonScore is one person's 0–5 score for one option: their ratings averaged
// by their own priorities. ok is false when they gave every rated point weight 0.
func PersonScore(features []Feature, w Weights, s Scores) (score float64, ok bool) {
	var num, den float64
	for _, f := range features {
		v, rated := s[f.Key]
		if !rated {
			continue
		}
		weight, set := w[f.Key]
		if !set {
			weight = DefaultWeight
		}
		num += v * float64(weight)
		den += float64(weight)
	}
	if den == 0 {
		return 0, false
	}
	return num / den, true
}

// PersonResult is one person's score inside an option's result.
type PersonResult struct {
	Person string  `json:"person"`
	Score  float64 `json:"score"`
}

// Result is one option's place in the ranking.
type Result struct {
	Option   string         `json:"option"`
	Score    float64        `json:"score"`
	RatedBy  int            `json:"rated_by"`
	Split    bool           `json:"split"`
	ByPerson []PersonResult `json:"by_person"`
}

// Rank combines everyone's answers: an option's score is the average of the
// scores of the people who rated it. Best first; options nobody rated go last.
func Rank(features []Feature, people []Person, options []Option) []Result {
	results := make([]Result, 0, len(options))
	for _, o := range options {
		r := Result{Option: o.ID, ByPerson: []PersonResult{}}
		var scores []float64
		for _, p := range people {
			s, rated := p.Ratings[o.ID]
			if !rated {
				continue
			}
			score, ok := PersonScore(features, p.Weights, s)
			if !ok {
				continue
			}
			scores = append(scores, score)
			r.ByPerson = append(r.ByPerson, PersonResult{Person: p.ID, Score: round(score)})
		}
		r.RatedBy = len(scores)
		if len(scores) > 0 {
			r.Score = round(mean(scores))
			r.Split = len(scores) >= 2 && stdev(scores) >= SplitThreshold
		}
		results = append(results, r)
	}
	sort.SliceStable(results, func(i, j int) bool {
		a, b := results[i], results[j]
		if (a.RatedBy == 0) != (b.RatedBy == 0) {
			return a.RatedBy > 0
		}
		return a.Score > b.Score
	})
	return results
}

func mean(xs []float64) float64 {
	var sum float64
	for _, x := range xs {
		sum += x
	}
	return sum / float64(len(xs))
}

// stdev is the sample standard deviation, as in the v1 app.
func stdev(xs []float64) float64 {
	m := mean(xs)
	var ss float64
	for _, x := range xs {
		ss += (x - m) * (x - m)
	}
	return math.Sqrt(ss / float64(len(xs)-1))
}

func round(x float64) float64 { return math.Round(x*100) / 100 }
