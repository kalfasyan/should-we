package migrations

import (
	"github.com/pocketbase/pocketbase/core"
	m "github.com/pocketbase/pocketbase/migrations"
)

// All collections stay superuser-only (nil rules). People reach a decision
// through its link, so the app's own routes in app/routes.go do the access checks.
func init() {
	m.Register(func(app core.App) error {
		decisions := core.NewBaseCollection("decisions")
		decisions.Fields.Add(
			&core.TextField{Name: "title", Required: true, Max: 120},
			&core.JSONField{Name: "features", Required: true},
			&core.AutodateField{Name: "created", OnCreate: true},
			&core.AutodateField{Name: "updated", OnCreate: true, OnUpdate: true},
		)
		if err := app.Save(decisions); err != nil {
			return err
		}

		people := core.NewBaseCollection("people")
		people.Fields.Add(
			&core.RelationField{Name: "decision", Required: true, MaxSelect: 1, CollectionId: decisions.Id, CascadeDelete: true},
			&core.TextField{Name: "name", Required: true, Max: 40},
			// proves "this browser is this person"; only the person's own browser knows it
			&core.TextField{Name: "token", Required: true, Hidden: true},
			&core.JSONField{Name: "weights"},
			&core.JSONField{Name: "ratings"},
			&core.AutodateField{Name: "created", OnCreate: true},
			&core.AutodateField{Name: "updated", OnCreate: true, OnUpdate: true},
		)
		people.AddIndex("idx_people_name", true, "decision, name COLLATE NOCASE", "")
		if err := app.Save(people); err != nil {
			return err
		}

		options := core.NewBaseCollection("options")
		options.Fields.Add(
			&core.RelationField{Name: "decision", Required: true, MaxSelect: 1, CollectionId: decisions.Id, CascadeDelete: true},
			&core.TextField{Name: "name", Required: true, Max: 120},
			&core.TextField{Name: "note", Max: 500},
			&core.RelationField{Name: "added_by", MaxSelect: 1, CollectionId: people.Id},
			&core.AutodateField{Name: "created", OnCreate: true},
			&core.AutodateField{Name: "updated", OnCreate: true, OnUpdate: true},
		)
		options.AddIndex("idx_options_name", true, "decision, name COLLATE NOCASE", "")
		return app.Save(options)
	}, func(app core.App) error {
		for _, name := range []string{"options", "people", "decisions"} {
			c, err := app.FindCollectionByNameOrId(name)
			if err != nil {
				return err
			}
			if err := app.Delete(c); err != nil {
				return err
			}
		}
		return nil
	})
}
