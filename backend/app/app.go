// Package app wires should-we's HTTP API into PocketBase.
package app

import (
	"github.com/pocketbase/pocketbase"
	"github.com/pocketbase/pocketbase/core"
)

func Register(pb *pocketbase.PocketBase) {
	pb.OnServe().BindFunc(func(se *core.ServeEvent) error {
		registerRoutes(se)
		return se.Next()
	})
}
