const 
    gulp = require('gulp'),
    sass = require('gulp-sass'),
    rename = require('gulp-rename'),
    terser = require('gulp-terser'),
    concat = require('gulp-concat'),
    gutil = require('gulp-util'),
    autoprefixer = require('gulp-autoprefixer'),
    eslint = require('gulp-eslint');

// static and templates folders
const
	static = 'app/static/',
	templates = 'app/templates/'

// boostrap scss source
const bootstrap = {
    in: './node_modules/bootstrap/'
};

// js
const js = {
	in: [static + 'es/helpers.js',
		 static + 'es/basicForm.js',
		 static + 'es/orgForm.js',
		 static + 'es/admin.js',
		 static + 'es/apiKeyForm.js',
		 static + 'es/listsTable.js',
		 static + 'es/charts.js'],
	out: static + 'js/'
};

// scss
const scss = {
	in: static + 'scss/main.scss',
	out: static + 'css/',
	outName: 'styles.min.css',
	watch: static + 'scss/**/*',
	sassOpts: {
		outputStyle: 'compressed',
		precision: 3,
		includePaths: [bootstrap.in + 'scss']
	}
};

// compile scss
gulp.task('scss', () => {
	return gulp.src(scss.in)
		.pipe(sass(scss.sassOpts))
		.on('error', gutil.log)
		.pipe(autoprefixer())
		.pipe(rename(scss.outName))
		.pipe(gulp.dest(scss.out));
});

// lint es
gulp.task('lint', () => {
	return gulp.src(js.in)
		.pipe(eslint())
		.pipe(eslint.format());
});

// uglify es
gulp.task('terser', async () => {
	return gulp.src(js.in)
		.pipe(concat('scripts.min.js'))
		.pipe(terser())
		.on('error', gutil.log)
		.pipe(gulp.dest(js.out));
});

// default task
gulp.task('default', 
	gulp.series(gulp.parallel('scss', gulp.series('lint', 'terser')), 
		() => {
			gulp.watch(scss.watch, gulp.series('scss'));
			gulp.watch(js.in, gulp.series('lint', 'terser'));
		}
	)
);
