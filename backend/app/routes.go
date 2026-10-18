package app

import (
	"crypto/rand"
	"crypto/subtle"
	"encoding/hex"
	"net/http"
	"strings"

	"github.com/pocketbase/dbx"
	"github.com/pocketbase/pocketbase/core"

	"github.com/kalfasyan/should-we/decide"
)

// A decision's id is its share link: anyone who has it can join, rate and see
// results. Changing your own priorities and ratings needs the token your
// browser got when you joined, sent as X-Person-Id and X-Person-Token.

type personView struct {
	ID      string                   `json:"id"`
	Name    string                   `json:"name"`
	Weights decide.Weights           `json:"weights"`
	Ratings map[string]decide.Scores `json:"ratings"`
}

type optionView struct {
	ID      string `json:"id"`
	Name    string `json:"name"`
	Note    string `json:"note"`
	AddedBy string `json:"added_by"`
}

type decisionView struct {
	ID       string           `json:"id"`
	Title    string           `json:"title"`
	Features []decide.Feature `json:"features"`
	People   []personView     `json:"people"`
	Options  []optionView     `json:"options"`
	Results  []decide.Result  `json:"results"`
}

func registerRoutes(se *core.ServeEvent) {
	g := se.Router.Group("/api/sw")
	g.POST("/decisions", createDecision)
	g.GET("/decisions/{id}", getDecision)
	g.POST("/decisions/{id}/people", joinDecision)
	g.PUT("/decisions/{id}/people/{pid}/weights", saveWeights)
	g.PUT("/decisions/{id}/people/{pid}/ratings/{oid}", saveRating)
	g.POST("/decisions/{id}/options", addOption)
	g.PATCH("/decisions/{id}/options/{oid}", editOption)
	g.DELETE("/decisions/{id}/options/{oid}", deleteOption)
}

func newToken() string {
	b := make([]byte, 24)
	_, _ = rand.Read(b)
	return hex.EncodeToString(b)
}

func loadDecision(e *core.RequestEvent) (*core.Record, []decide.Feature, error) {
	d, err := e.App.FindRecordById("decisions", e.Request.PathValue("id"))
	if err != nil {
		return nil, nil, e.NotFoundError("This decision doesn't exist. Check the link.", nil)
	}
	var features []decide.Feature
	if err := d.UnmarshalJSONField("features", &features); err != nil {
		return nil, nil, e.InternalServerError("", err)
	}
	return d, features, nil
}

func loadPeople(app core.App, decisionID string) ([]*core.Record, error) {
	return app.FindRecordsByFilter("people", "decision = {:d}", "created", 0, 0, dbx.Params{"d": decisionID})
}

func loadOptions(app core.App, decisionID string) ([]*core.Record, error) {
	return app.FindRecordsByFilter("options", "decision = {:d}", "created", 0, 0, dbx.Params{"d": decisionID})
}

func toPerson(r *core.Record) decide.Person {
	p := decide.Person{ID: r.Id, Name: r.GetString("name"), Weights: decide.Weights{}, Ratings: map[string]decide.Scores{}}
	_ = r.UnmarshalJSONField("weights", &p.Weights)
	_ = r.UnmarshalJSONField("ratings", &p.Ratings)
	if p.Weights == nil {
		p.Weights = decide.Weights{}
	}
	if p.Ratings == nil {
		p.Ratings = map[string]decide.Scores{}
	}
	return p
}

// me returns the person making the request, checking their token.
func me(e *core.RequestEvent, decisionID, personID string) (*core.Record, error) {
	if personID == "" {
		personID = e.Request.Header.Get("X-Person-Id")
	}
	p, err := e.App.FindRecordById("people", personID)
	token := e.Request.Header.Get("X-Person-Token")
	if err != nil || p.GetString("decision") != decisionID || token == "" ||
		subtle.ConstantTimeCompare([]byte(token), []byte(p.GetString("token"))) != 1 {
		return nil, e.ForbiddenError("Join this decision first.", nil)
	}
	return p, nil
}

func createDecision(e *core.RequestEvent) error {
	var body struct {
		Title    string   `json:"title"`
		Features []string `json:"features"`
	}
	if err := e.BindBody(&body); err != nil {
		return e.BadRequestError("", err)
	}
	title := strings.TrimSpace(body.Title)
	if title == "" || len([]rune(title)) > 120 {
		return e.BadRequestError("Give it a name of up to 120 characters.", nil)
	}
	features, err := decide.Features(body.Features)
	if err != nil {
		return e.BadRequestError(capitalize(err.Error())+".", nil)
	}
	col, err := e.App.FindCollectionByNameOrId("decisions")
	if err != nil {
		return e.InternalServerError("", err)
	}
	d := core.NewRecord(col)
	d.Set("title", title)
	d.Set("features", features)
	if err := e.App.Save(d); err != nil {
		return e.InternalServerError("", err)
	}
	return e.JSON(http.StatusOK, map[string]string{"id": d.Id})
}

func getDecision(e *core.RequestEvent) error {
	d, features, err := loadDecision(e)
	if err != nil {
		return err
	}
	view, err := buildView(e.App, d, features)
	if err != nil {
		return e.InternalServerError("", err)
	}
	return e.JSON(http.StatusOK, view)
}

func buildView(app core.App, d *core.Record, features []decide.Feature) (*decisionView, error) {
	peopleRecs, err := loadPeople(app, d.Id)
	if err != nil {
		return nil, err
	}
	optionRecs, err := loadOptions(app, d.Id)
	if err != nil {
		return nil, err
	}
	view := &decisionView{ID: d.Id, Title: d.GetString("title"), Features: features,
		People: []personView{}, Options: []optionView{}}
	people := make([]decide.Person, len(peopleRecs))
	for i, r := range peopleRecs {
		people[i] = toPerson(r)
		view.People = append(view.People, personView{people[i].ID, people[i].Name, people[i].Weights, people[i].Ratings})
	}
	options := make([]decide.Option, len(optionRecs))
	for i, r := range optionRecs {
		options[i] = decide.Option{ID: r.Id, Name: r.GetString("name"), Note: r.GetString("note")}
		view.Options = append(view.Options, optionView{r.Id, options[i].Name, options[i].Note, r.GetString("added_by")})
	}
	view.Results = decide.Rank(features, people, options)
	return view, nil
}

func joinDecision(e *core.RequestEvent) error {
	d, features, err := loadDecision(e)
	if err != nil {
		return err
	}
	var body struct {
		Name string `json:"name"`
	}
	if err := e.BindBody(&body); err != nil {
		return e.BadRequestError("", err)
	}
	name := strings.TrimSpace(body.Name)
	if name == "" || len([]rune(name)) > 40 {
		return e.BadRequestError("Enter a name of up to 40 characters.", nil)
	}
	people, err := loadPeople(e.App, d.Id)
	if err != nil {
		return e.InternalServerError("", err)
	}
	for _, p := range people {
		if strings.EqualFold(p.GetString("name"), name) {
			return e.BadRequestError("Someone already joined as "+p.GetString("name")+". Pick another name.", nil)
		}
	}
	col, err := e.App.FindCollectionByNameOrId("people")
	if err != nil {
		return e.InternalServerError("", err)
	}
	token := newToken()
	p := core.NewRecord(col)
	p.Set("decision", d.Id)
	p.Set("name", name)
	p.Set("token", token)
	p.Set("weights", decide.DefaultWeights(features))
	p.Set("ratings", map[string]decide.Scores{})
	if err := e.App.Save(p); err != nil {
		return e.InternalServerError("", err)
	}
	return e.JSON(http.StatusOK, map[string]string{"id": p.Id, "name": name, "token": token})
}

func saveWeights(e *core.RequestEvent) error {
	d, features, err := loadDecision(e)
	if err != nil {
		return err
	}
	p, err := me(e, d.Id, e.Request.PathValue("pid"))
	if err != nil {
		return err
	}
	var body decide.Weights
	if err := e.BindBody(&body); err != nil {
		return e.BadRequestError("", err)
	}
	clean, err := decide.CleanWeights(features, body)
	if err != nil {
		return e.BadRequestError(capitalize(err.Error())+".", nil)
	}
	weights := toPerson(p).Weights
	for k, v := range clean {
		weights[k] = v
	}
	p.Set("weights", weights)
	if err := e.App.Save(p); err != nil {
		return e.InternalServerError("", err)
	}
	return e.NoContent(http.StatusNoContent)
}

func saveRating(e *core.RequestEvent) error {
	d, features, err := loadDecision(e)
	if err != nil {
		return err
	}
	p, err := me(e, d.Id, e.Request.PathValue("pid"))
	if err != nil {
		return err
	}
	o, err := e.App.FindRecordById("options", e.Request.PathValue("oid"))
	if err != nil || o.GetString("decision") != d.Id {
		return e.NotFoundError("This option was removed.", nil)
	}
	var body decide.Scores
	if err := e.BindBody(&body); err != nil {
		return e.BadRequestError("", err)
	}
	clean, err := decide.CleanScores(features, body)
	if err != nil {
		return e.BadRequestError(capitalize(err.Error())+".", nil)
	}
	ratings := toPerson(p).Ratings
	ratings[o.Id] = clean
	p.Set("ratings", ratings)
	if err := e.App.Save(p); err != nil {
		return e.InternalServerError("", err)
	}
	return e.NoContent(http.StatusNoContent)
}

type optionBody struct {
	Name string `json:"name"`
	Note string `json:"note"`
}

func addOption(e *core.RequestEvent) error {
	d, _, err := loadDecision(e)
	if err != nil {
		return err
	}
	p, err := me(e, d.Id, "")
	if err != nil {
		return err
	}
	var body optionBody
	if err := e.BindBody(&body); err != nil {
		return e.BadRequestError("", err)
	}
	name, note := strings.TrimSpace(body.Name), strings.TrimSpace(body.Note)
	if name == "" || len([]rune(name)) > 120 {
		return e.BadRequestError("Give the option a name of up to 120 characters.", nil)
	}
	if len([]rune(note)) > 500 {
		return e.BadRequestError("Keep the note under 500 characters.", nil)
	}
	options, err := loadOptions(e.App, d.Id)
	if err != nil {
		return e.InternalServerError("", err)
	}
	for _, o := range options {
		if strings.EqualFold(o.GetString("name"), name) {
			return e.BadRequestError(o.GetString("name")+" is already on the list.", nil)
		}
	}
	col, err := e.App.FindCollectionByNameOrId("options")
	if err != nil {
		return e.InternalServerError("", err)
	}
	o := core.NewRecord(col)
	o.Set("decision", d.Id)
	o.Set("name", name)
	o.Set("note", note)
	o.Set("added_by", p.Id)
	if err := e.App.Save(o); err != nil {
		return e.InternalServerError("", err)
	}
	return e.JSON(http.StatusOK, optionView{o.Id, name, note, p.Id})
}

func findOption(e *core.RequestEvent, decisionID string) (*core.Record, error) {
	o, err := e.App.FindRecordById("options", e.Request.PathValue("oid"))
	if err != nil || o.GetString("decision") != decisionID {
		return nil, e.NotFoundError("This option was removed.", nil)
	}
	return o, nil
}

func editOption(e *core.RequestEvent) error {
	d, _, err := loadDecision(e)
	if err != nil {
		return err
	}
	if _, err := me(e, d.Id, ""); err != nil {
		return err
	}
	o, err := findOption(e, d.Id)
	if err != nil {
		return err
	}
	var body optionBody
	if err := e.BindBody(&body); err != nil {
		return e.BadRequestError("", err)
	}
	note := strings.TrimSpace(body.Note)
	if len([]rune(note)) > 500 {
		return e.BadRequestError("Keep the note under 500 characters.", nil)
	}
	o.Set("note", note)
	if err := e.App.Save(o); err != nil {
		return e.InternalServerError("", err)
	}
	return e.NoContent(http.StatusNoContent)
}

// deleteOption removes an option and everyone's ratings of it.
func deleteOption(e *core.RequestEvent) error {
	d, _, err := loadDecision(e)
	if err != nil {
		return err
	}
	if _, err := me(e, d.Id, ""); err != nil {
		return err
	}
	o, err := findOption(e, d.Id)
	if err != nil {
		return err
	}
	err = e.App.RunInTransaction(func(tx core.App) error {
		people, err := loadPeople(tx, d.Id)
		if err != nil {
			return err
		}
		for _, r := range people {
			ratings := toPerson(r).Ratings
			if _, ok := ratings[o.Id]; !ok {
				continue
			}
			delete(ratings, o.Id)
			r.Set("ratings", ratings)
			if err := tx.Save(r); err != nil {
				return err
			}
		}
		return tx.Delete(o)
	})
	if err != nil {
		return e.InternalServerError("", err)
	}
	return e.NoContent(http.StatusNoContent)
}

func capitalize(s string) string {
	if s == "" {
		return s
	}
	return strings.ToUpper(s[:1]) + s[1:]
}
