package main

import (
	"log"
	"net/http"
	"os"

	"github.com/pocketbase/pocketbase"
	"github.com/pocketbase/pocketbase/apis"
	"github.com/pocketbase/pocketbase/core"
	"github.com/pocketbase/pocketbase/plugins/migratecmd"

	"github.com/selfhostit/should-we/app"
	_ "github.com/selfhostit/should-we/migrations"
)

func main() {
	pb := pocketbase.New()

	var publicDir string
	pb.RootCmd.PersistentFlags().StringVar(&publicDir, "publicDir", "./pb_public", "the directory with the built web app")
	_ = pb.RootCmd.ParseFlags(os.Args[1:])

	// migrations live in Go code; never auto-generate them from admin UI edits
	migratecmd.MustRegister(pb, pb.RootCmd, migratecmd.Config{
		TemplateLang: migratecmd.TemplateLangGo,
		Automigrate:  false,
	})

	app.Register(pb)

	// serve the web app, falling back to index.html for client-side routes
	pb.OnServe().BindFunc(func(se *core.ServeEvent) error {
		if !se.Router.HasRoute(http.MethodGet, "/{path...}") {
			se.Router.GET("/{path...}", apis.Static(os.DirFS(publicDir), true))
		}
		return se.Next()
	})

	if err := pb.Start(); err != nil {
		log.Fatal(err)
	}
}
